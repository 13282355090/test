import streamlit as st
import os
import csv
import random
from collections import defaultdict
from trueskill import Rating, rate_1vs1
from PIL import Image

IMAGE_FOLDER = "images"
PERCEPTIONS = ["美丽"]          # 你可以按需改成多维度
RESULT_CSV_TEMPLATE = "comparison_results_{}.csv"
COUNT_CSV = "image_comparison_counts.csv"

# 初始化图片列表
ALL_IMAGES = [
    os.path.join(IMAGE_FOLDER, img)
    for img in os.listdir(IMAGE_FOLDER)
    if img.lower().endswith(('jpg', 'jpeg', 'png'))
]

# ===================== 辅助函数：统计当前用户已完成对比次数 =====================
def get_user_comparison_count(user_id: str) -> int:
    """遍历所有结果 CSV，统计指定 user_id 的对比记录条数"""
    total = 0
    for dim in PERCEPTIONS:
        file_path = RESULT_CSV_TEMPLATE.format(dim)
        if os.path.exists(file_path):
            with open(file_path, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('User_ID') == user_id:
                        total += 1
    return total
# ==============================================================================

# ---------------------- 管理员登录与数据下载 ----------------------
st.sidebar.subheader("管理员登录")
admin_password = st.sidebar.text_input("请输入管理员密码", type="password")

if admin_password == "2023202090005":
    st.sidebar.success("身份验证成功")
    st.success("密码正确，请点击下方按钮下载所有结果文件：")

    if os.path.exists(COUNT_CSV):
        with open(COUNT_CSV, "rb") as f:
            st.download_button(
                label="📊 下载图片比较次数统计",
                data=f,
                file_name="image_comparison_counts.csv",
                mime="text/csv"
            )

    for dim in PERCEPTIONS:
        output_file = RESULT_CSV_TEMPLATE.format(dim)
        if os.path.exists(output_file):
            with open(output_file, "rb") as f:
                st.download_button(
                    label=f"⬇️ 下载 {dim} 结果文件",
                    data=f,
                    file_name=output_file,
                    mime="text/csv"
                )
    st.stop()

# ---------------------- 用户 ID 输入 ----------------------
if 'user_id' not in st.session_state:
    user_id_input = st.text_input("请输入你的用户ID以开始（可以是任何字符，多次填写输入相同ID即可）：")
    if user_id_input:
        st.session_state.user_id = user_id_input
        # ==== 新增开始 ====
        st.session_state.user_comparison_count = get_user_comparison_count(user_id_input)
        # ==== 新增结束 ====
        st.rerun()
    else:
        st.stop()

# ================= 显示当前用户对比次数（在侧边栏或页面顶部） ================
# ---- 侧边栏展示 ----
st.sidebar.markdown(
    f"🧮 你已完成对比：**{st.session_state.get('user_comparison_count', 0)}** 次"
)
# ---- 页面顶部也可以展示（如不需要可删除）----
st.info(f"当前用户 **{st.session_state.user_id}** 已完成对比："
        f"**{st.session_state.get('user_comparison_count', 0)}** 次")
# ==============================================================================

# ---------------------- 初始化状态 ----------------------
if 'ratings' not in st.session_state:
    st.session_state.ratings = defaultdict(lambda: Rating())
    st.session_state.comparison_counts = {
        img: [0] * len(PERCEPTIONS) for img in ALL_IMAGES
    }
    st.session_state.current_dim = 0

# ---------------------- 加载已有比较次数数据 ----------------------
if os.path.exists(COUNT_CSV):
    with open(COUNT_CSV, newline='') as f:
        reader = csv.reader(f)
        next(reader, None)  # 跳过表头
        for row in reader:
            name = os.path.join(IMAGE_FOLDER, row[0])
            if name in st.session_state.comparison_counts:
                st.session_state.comparison_counts[name] = list(map(int, row[1:]))

# ---------------------- 维度切换逻辑 ----------------------
def check_current_dim_complete():
    return all(
        counts[st.session_state.current_dim] >= 5
        for counts in st.session_state.comparison_counts.values()
    )

while (
    st.session_state.current_dim < len(PERCEPTIONS)
    and check_current_dim_complete()
):
    st.session_state.current_dim += 1

if st.session_state.current_dim >= len(PERCEPTIONS):
    st.success("所有维度对比已完成，感谢您的参与！")
    st.stop()

current_dim_name = PERCEPTIONS[st.session_state.current_dim]
result_csv = RESULT_CSV_TEMPLATE.format(current_dim_name)

# ---------------------- 随机抽取图片对 ----------------------
def weighted_random_pair():
    valid_images = [
        img
        for img in ALL_IMAGES
        if st.session_state.comparison_counts[img][st.session_state.current_dim] < 5
    ]
    if not valid_images:
        st.success("所有图片都已对比 5 次，感谢您的参与！")
        st.stop()

    weights = [
        1 / (1 + st.session_state.comparison_counts[img][st.session_state.current_dim])
        for img in valid_images
    ]
    pair = random.choices(valid_images, weights=weights, k=2)
    while pair[0] == pair[1]:
        pair[1] = random.choices(valid_images, weights=weights, k=1)[0]
    return pair

left_img, right_img = weighted_random_pair()

# ---------------------- 显示图片与选择按钮 ----------------------
st.title(f"您认为哪张图片更『{current_dim_name}』？")
st.subheader(f"当前对比维度: {current_dim_name}")

col1, col2 = st.columns(2)
with col1:
    st.image(Image.open(left_img), use_container_width=True)
    st.markdown(f"<h4>左图</h4>: {os.path.basename(left_img)}", unsafe_allow_html=True)
    st.write(
        f"对比次数: "
        f"{st.session_state.comparison_counts[left_img][st.session_state.current_dim]}"
    )

with col2:
    st.image(Image.open(right_img), use_container_width=True)
    st.markdown(f"<h4>右图</h4>: {os.path.basename(right_img)}", unsafe_allow_html=True)
    st.write(
        f"对比次数: "
        f"{st.session_state.comparison_counts[right_img][st.session_state.current_dim]}"
    )

st.markdown(f"### 您认为哪张图片更『{current_dim_name}』？")

# ---------------------- 记录结果 / 更新状态 ----------------------
def record_result(result):
    l, r = left_img, right_img
    if result == "left":
        st.session_state.ratings[l], st.session_state.ratings[r] = rate_1vs1(
            st.session_state.ratings[l], st.session_state.ratings[r]
        )
    elif result == "right":
        st.session_state.ratings[r], st.session_state.ratings[l] = rate_1vs1(
            st.session_state.ratings[r], st.session_state.ratings[l]
        )
    else:
        st.session_state.ratings[l], st.session_state.ratings[r] = rate_1vs1(
            st.session_state.ratings[l],
            st.session_state.ratings[r],
            drawn=True
        )

    # 更新比较次数
    st.session_state.comparison_counts[l][st.session_state.current_dim] += 1
    st.session_state.comparison_counts[r][st.session_state.current_dim] += 1

    # ==== 新增：当前用户对比次数 +1 ====
    st.session_state.user_comparison_count += 1
    # ==================================

    # 保存结果
    with open(result_csv, 'a', newline='') as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow([
                'User_ID', 'Left_Image', 'Right_Image',
                'Result', 'Left_Rating', 'Right_Rating'
            ])
        writer.writerow([
            st.session_state.user_id,
            os.path.basename(l),
            os.path.basename(r),
            result,
            f"{st.session_state.ratings[l].mu:.3f}±{st.session_state.ratings[l].sigma:.3f}",
            f"{st.session_state.ratings[r].mu:.3f}±{st.session_state.ratings[r].sigma:.3f}"
        ])

    # 更新次数统计 CSV
    with open(COUNT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Image"] + list(range(len(PERCEPTIONS))))
        for img, counts in st.session_state.comparison_counts.items():
            writer.writerow([os.path.basename(img)] + counts)

    st.rerun()

# ---------------------- 三个选择按钮 ----------------------
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
