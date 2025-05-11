import random
import csv
import os
import streamlit as st
from trueskill import Rating, rate_1vs1
from PIL import Image
from collections import defaultdict

# 配置路径
IMAGE_FOLDER = "images"
OUTPUT_FILES = {
    "comparison_results_beautiful.csv": "comparison_results_beautiful.csv",
    "comparison_results_boring.csv": "comparison_results_boring.csv",
    "comparison_results_depressing.csv": "comparison_results_depressing.csv",
    "comparison_results_lively.csv": "comparison_results_lively.csv",
    "comparison_results_safety.csv": "comparison_results_safety.csv",
    "comparison_results_wealthy.csv": "comparison_results_wealthy.csv"
}
COUNT_CSV = "image_comparison_counts.csv"
IMAGES = [f for f in os.listdir(IMAGE_FOLDER) if f.endswith(('.jpg', '.png', '.jpeg'))]

# 管理员登录
st.sidebar.subheader("管理员登录")
admin_password = st.sidebar.text_input("请输入管理员密码", type="password")

if admin_password == "2023202090005":
    st.sidebar.success("身份验证成功")
    st.success("密码正确，请点击下方按钮下载所有结果文件：")
    
    if os.path.exists(COUNT_CSV):
        with open(COUNT_CSV, "rb") as f:
            bytes_data = f.read()
            st.download_button(
                label="📊 下载图片比较次数统计",
                data=bytes_data,
                file_name="image_comparison_counts.csv",
                mime="text/csv"
            )
    for output_file in OUTPUT_FILES.values():
        if os.path.exists(output_file):
            with open(output_file, "rb") as f:
                file_bytes = f.read()
                label_name = output_file.replace("comparison_results_", "").replace(".csv", "")
                st.download_button(
                    label=f"⬇️ 下载 {label_name} 结果文件",
                    data=file_bytes,
                    file_name=output_file,
                    mime="text/csv"
                )
    st.stop()

# 用户 ID 输入
if 'user_id' not in st.session_state:
    user_id_input = st.text_input("请输入你的用户ID以开始：")
    if user_id_input:
        st.session_state.user_id = user_id_input
        st.rerun()  # Use st.rerun() instead of st.experimental_rerun()
    else:
        st.stop()

# 初始化状态
if 'initialized' not in st.session_state:
    st.session_state.ratings = defaultdict(lambda: Rating())
    st.session_state.comparison_counts = defaultdict(int)
    st.session_state.need_rerun = False

# 加载或初始化对比次数统计文件
if not os.path.exists(COUNT_CSV):
    with open(COUNT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Image', 'Comparison_Count'])
        for image in IMAGES:
            writer.writerow([image, 0])

# 读取当前对比次数
def read_comparison_counts():
    comparison_counts = defaultdict(int)
    if os.path.exists(COUNT_CSV):
        with open(COUNT_CSV, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # 跳过标题
            for row in reader:
                comparison_counts[row[0]] = int(row[1])
    return comparison_counts

# 更新对比次数并保存
def update_comparison_counts():
    with open(COUNT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Image', 'Comparison_Count'])
        for image, count in st.session_state.comparison_counts.items():
            writer.writerow([image, count])

# 选择图片对比
def select_image_pair():
    comparison_counts = read_comparison_counts()
    
    # 按照概率减少已出现次数多的图片的出现概率
    weighted_images = []
    for image in IMAGES:
        weight = 1 / (comparison_counts[image] + 1)  # 防止除零
        weighted_images.extend([image] * int(weight * 100))  # 权重影响选择频率
    
    # 随机选择两个不一样的图片
    random.shuffle(weighted_images)
    left_img, right_img = weighted_images[0], weighted_images[1]
    
    # 更新比较次数
    st.session_state.comparison_counts[left_img] += 1
    st.session_state.comparison_counts[right_img] += 1
    update_comparison_counts()
    
    return os.path.join(IMAGE_FOLDER, left_img), os.path.join(IMAGE_FOLDER, right_img)

# 主逻辑
if st.session_state.get("need_rerun", False):
    st.session_state.need_rerun = False
    st.rerun()

# 显示当前图片对比
left_img, right_img = select_image_pair()

st.title("街景图片对比评分系统")
st.subheader("请选择您更喜欢的图片")

col1, col2 = st.columns(2)
with col1:
    st.image(Image.open(left_img), use_container_width=True, caption=f"左图: {os.path.basename(left_img)}")
with col2:
    st.image(Image.open(right_img), use_container_width=True, caption=f"右图: {os.path.basename(right_img)}")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("⬅️ 选择左侧", use_container_width=True):
        result = "left"
        record_selection(result, left_img, right_img)

with col2:
    if st.button("🟰 两者相当", use_container_width=True):
        result = "equal"
        record_selection(result, left_img, right_img)

with col3:
    if st.button("➡️ 选择右侧", use_container_width=True):
        result = "right"
        record_selection(result, left_img, right_img)

# 记录选择结果
def record_selection(result, left_img, right_img):
    try:
        if result == "left":
            st.session_state.ratings[left_img], st.session_state.ratings[right_img] = rate_1vs1(
                st.session_state.ratings[left_img], st.session_state.ratings[right_img], drawn=False)
        elif result == "right":
            st.session_state.ratings[right_img], st.session_state.ratings[left_img] = rate_1vs1(
                st.session_state.ratings[right_img], st.session_state.ratings[left_img], drawn=False)
        else:
            st.session_state.ratings[left_img], st.session_state.ratings[right_img] = rate_1vs1(
                st.session_state.ratings[left_img], st.session_state.ratings[right_img], drawn=True)

        # 写入对比结果到文件
        current_file = OUTPUT_FILES.get("comparison_results_beautiful.csv")  # 在此添加您选择的对应文件
        with open(current_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                st.session_state.user_id,
                os.path.basename(left_img),
                os.path.basename(right_img),
                result,
                f"{st.session_state.ratings[left_img].mu:.3f}±{st.session_state.ratings[left_img].sigma:.3f}",
                f"{st.session_state.ratings[right_img].mu:.3f}±{st.session_state.ratings[right_img].sigma:.3f}"
            ])

        st.session_state.need_rerun = True

    except Exception as e:
        st.error(f"记录选择时出错: {str(e)}")
