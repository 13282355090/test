import streamlit as st
import os
import csv
import random
from collections import defaultdict
from trueskill import Rating, rate_1vs1
from PIL import Image

IMAGE_FOLDER = "images"
PERCEPTIONS = ["美丽", "无聊", "压抑", "活力", "安全", "富有"]
RESULT_CSV_TEMPLATE = "comparison_results_{}.csv"
COUNT_CSV = "image_comparison_counts.csv"

# 初始化图片列表
ALL_IMAGES = [os.path.join(IMAGE_FOLDER, img) for img in os.listdir(IMAGE_FOLDER)
               if img.lower().endswith(('jpg', 'jpeg', 'png'))]

# 选择维度
selected_dim = st.selectbox("请选择您要对比的感知维度：", options=PERCEPTIONS, index=0)

dim_index = PERCEPTIONS.index(selected_dim)
result_csv = RESULT_CSV_TEMPLATE.format(selected_dim)

# 用户 ID 输入
if 'user_id' not in st.session_state:
    user_id_input = st.text_input("请输入你的用户ID以开始：")
    if user_id_input:
        st.session_state.user_id = user_id_input
        st.rerun()
    else:
        st.stop()

# 初始化状态
if 'ratings' not in st.session_state:
    st.session_state.ratings = defaultdict(lambda: Rating())
    st.session_state.comparison_counts = {img: [0]*len(PERCEPTIONS) for img in ALL_IMAGES}

# 加载已有比较数据
if os.path.exists(COUNT_CSV):
    with open(COUNT_CSV, newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            name = os.path.join(IMAGE_FOLDER, row[0])
            if name in st.session_state.comparison_counts:
                st.session_state.comparison_counts[name] = list(map(int, row[1:]))

# 权重策略（次数越多，权重越小）
def weighted_random_pair():
    weights = [1 / (1 + st.session_state.comparison_counts[img][dim_index]) for img in ALL_IMAGES]
    pair = random.choices(ALL_IMAGES, weights=weights, k=2)
    while pair[0] == pair[1]:
        pair[1] = random.choices(ALL_IMAGES, weights=weights, k=1)[0]
    return pair

left_img, right_img = weighted_random_pair()

# 显示图像
st.title("街景图片对比评分系统")
st.subheader(f"当前对比维度: {selected_dim}")

col1, col2 = st.columns(2)
with col1:
    st.image(Image.open(left_img), use_container_width=True, caption=f"左图: {os.path.basename(left_img)}")
    st.write(f"对比次数: {st.session_state.comparison_counts[left_img][dim_index]}")
with col2:
    st.image(Image.open(right_img), use_container_width=True, caption=f"右图: {os.path.basename(right_img)}")
    st.write(f"对比次数: {st.session_state.comparison_counts[right_img][dim_index]}")

def record_result(result):
    l, r = left_img, right_img
    if result == "left":
        st.session_state.ratings[l], st.session_state.ratings[r] = rate_1vs1(st.session_state.ratings[l], st.session_state.ratings[r])
    elif result == "right":
        st.session_state.ratings[r], st.session_state.ratings[l] = rate_1vs1(st.session_state.ratings[r], st.session_state.ratings[l])
    else:
        st.session_state.ratings[l], st.session_state.ratings[r] = rate_1vs1(st.session_state.ratings[l], st.session_state.ratings[r], drawn=True)

    st.session_state.comparison_counts[l][dim_index] += 1
    st.session_state.comparison_counts[r][dim_index] += 1

    with open(result_csv, 'a', newline='') as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow(['User_ID', 'Left_Image', 'Right_Image', 'Result', 'Left_Rating', 'Right_Rating'])
        writer.writerow([
            st.session_state.user_id,
            os.path.basename(l),
            os.path.basename(r),
            result,
            f"{st.session_state.ratings[l].mu:.3f}±{st.session_state.ratings[l].sigma:.3f}",
            f"{st.session_state.ratings[r].mu:.3f}±{st.session_state.ratings[r].sigma:.3f}"
        ])

    # 更新次数统计CSV
    with open(COUNT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Image"] + list(range(len(PERCEPTIONS))))
        for img, counts in st.session_state.comparison_counts.items():
            writer.writerow([os.path.basename(img)] + counts)

    st.rerun()

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("⬅️ 选择左侧", use_container_width=True):
        record_result("left")
with col2:
    if st.button("🟰 两者相当", use_container_width=True):
        record_result("equal")
with col3:
    if st.button("➡️ 选择右侧", use_container_width=True):
        record_result("right")
