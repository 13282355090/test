import streamlit as st
import os
import random
import csv
from collections import defaultdict
from trueskill import Rating, rate_1vs1
from PIL import Image

# 配置路径
IMAGE_FOLDER = "images"
PAIRS_FILES = [
    "comparison_pairs_beautiful.csv", "comparison_pairs_boring.csv",
    "comparison_pairs_depressing.csv", "comparison_pairs_lively.csv",
    "comparison_pairs_safety.csv", "comparison_pairs_wealthy.csv"
]
OUTPUT_FILES = {
    "comparison_pairs_beautiful.csv": "comparison_results_beautiful.csv",
    "comparison_pairs_boring.csv": "comparison_results_boring.csv",
    "comparison_pairs_depressing.csv": "comparison_results_depressing.csv",
    "comparison_pairs_lively.csv": "comparison_results_lively.csv",
    "comparison_pairs_safety.csv": "comparison_results_safety.csv",
    "comparison_pairs_wealthy.csv": "comparison_results_wealthy.csv"
}
COUNT_CSV = "image_comparison_counts.csv"

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

    for input_file, output_file in OUTPUT_FILES.items():
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
    st.session_state.image_pairs = []
    st.session_state.current_pair_index = 0
    st.session_state.initialized = False
    st.session_state.need_rerun = False
    st.session_state.current_file_index = 0

TITLE_MAP = {
    0: "美丽", 1: "无聊", 2: "压抑", 3: "活力", 4: "安全", 5: "财富"
}
SELECT_TEXT_MAP = {
    0: "请选择哪张图片让你感到更加美丽:",
    1: "请选择哪张图片让你感到更加无聊:",
    2: "请选择哪张图片让你感到更加压抑:",
    3: "请选择哪张图片让你感到更加有活力:",
    4: "请选择哪张图片让你感到更加安全:",
    5: "请选择哪张图片让你感到更加富有:"
}

def initialize_app():
    while st.session_state.current_file_index < len(PAIRS_FILES):
        current_file = PAIRS_FILES[st.session_state.current_file_index]
        st.session_state.image_pairs = []

        # 获取所有图片
        image_files = [img for img in os.listdir(IMAGE_FOLDER) if img.endswith(('.jpg', '.png', '.jpeg'))]
        for img in image_files:
            st.session_state.comparison_counts[img] = 0  # 初始化所有图片的对比次数为0

        # 创建一个统计每张图片的对比次数的CSV
        if not os.path.exists(COUNT_CSV):
            with open(COUNT_CSV, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Image', 'Comparison_Count'])
                for img in image_files:
                    writer.writerow([img, 0])

        # 初始化感知对比数据文件
        if not os.path.exists(OUTPUT_FILES[current_file]):
            with open(OUTPUT_FILES[current_file], 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['User_ID', 'Left_Image', 'Right_Image', 'Result', 'Left_Rating', 'Right_Rating'])

        st.session_state.initialized = True
        return

    st.success("所有对比计划已完成！")
    st.stop()

def update_comparison_counts():
    """更新所有图片的对比次数并写入 CSV 文件"""
    with open(COUNT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Image', 'Comparison_Count'])
        for img, count in st.session_state.comparison_counts.items():
            writer.writerow([img, count])

def get_next_pair():
    """生成随机对比对，每次选择两张图片进行对比，避免对比次数过少的图片"""
    # 筛选出对比次数少于4次的图片
    possible_images = [img for img, count in st.session_state.comparison_counts.items() if count < 4]
    
    if len(possible_images) < 2:
        st.warning("没有足够的图片进行比较！")
        return None, None

    # 随机选择两张图片，避免重复
    left_img, right_img = random.sample(possible_images, 2)

    # 更新对比次数
    st.session_state.comparison_counts[left_img] += 1
    st.session_state.comparison_counts[right_img] += 1

    # 更新对比次数到CSV
    update_comparison_counts()

    return left_img, right_img

def show_current_pair(left_img, right_img):
    st.title("街景图片对比评分系统")
    st.subheader(f"当前对比计划: {TITLE_MAP[st.session_state.current_file_index]}")
    st.write(f"**进度**: {st.session_state.current_pair_index + 1}/{len(st.session_state.image_pairs)}")
    st.write(f"### {SELECT_TEXT_MAP[st.session_state.current_file_index]}")

    col1, col2 = st.columns(2)
    try:
        with col1:
            st.image(Image.open(left_img), use_container_width=True, caption=f"左图: {os.path.basename(left_img)}")
            st.write(f"已比较次数: {st.session_state.comparison_counts[left_img]}")
        with col2:
            st.image(Image.open(right_img), use_container_width=True, caption=f"右图: {os.path.basename(right_img)}")
            st.write(f"已比较次数: {st.session_state.comparison_counts[right_img]}")
    except Exception as e:
        st.error(f"加载图片失败: {str(e)}")
        st.session_state.need_rerun = True
        return None

    return True

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

        # 记录对比结果
        current_file = PAIRS_FILES[st.session_state.current_file_index]
        output_file = OUTPUT_FILES[current_file]
        with open(output_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([st.session_state.user_id, os.path.basename(left_img), os.path.basename(right_img),
                             result, f"{st.session_state.ratings[left_img].mu:.3f}±{st.session_state.ratings[left_img].sigma:.3f}",
                             f"{st.session_state.ratings[right_img].mu:.3f}±{st.session_state.ratings[right_img].sigma:.3f}"])

        st.session_state.need_rerun = True

    except Exception as e:
        st.error(f"记录选择时出错: {str(e)}")

# 主逻辑
if not st.session_state.initialized:
    initialize_app()

if st.session_state.initialized:
    left_img, right_img = get_next_pair()
    if left_img and right_img:
        if show_current_pair(left_img, right_img):
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("⬅️ 选择左侧", use_container_width=True):
                    record_selection("left", left_img, right_img)
            with col2:
                if st.button("🟰 两者相当", use_container_width=True):
                    record_selection("equal", left_img, right_img)
            with col3:
                if st.button("➡️ 选择右侧", use_container_width=True):
                    record_selection("right", left_img, right_img)

if st.session_state.get("need_rerun", False):
    st.session_state.need_rerun = False
    st.rerun()
