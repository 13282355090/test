import streamlit as st
import os
import csv
from itertools import combinations
from collections import defaultdict
from trueskill import Rating, rate_1vs1
from PIL import Image

# 配置路径
IMAGE_FOLDER = "images"
PER_IMAGE_MIN_COMPARISONS = 2
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

# 管理员登录
st.sidebar.subheader("管理员登录")
admin_password = st.sidebar.text_input("请输入管理员密码", type="password")
if admin_password == "2023202090005":
    st.sidebar.success("身份验证成功")
    st.success("密码正确，管理员无需参与对比任务。")
    st.stop()

# 用户 ID 输入
if 'user_id' not in st.session_state:
    user_id_input = st.text_input("请输入你的用户ID以开始：")
    if user_id_input:
        st.session_state.user_id = user_id_input
        st.rerun()
    else:
        st.stop()

# 初始化状态
if 'initialized' not in st.session_state:
    st.session_state.ratings = defaultdict(lambda: Rating())
    st.session_state.comparison_counts = defaultdict(int)
    st.session_state.image_counts_by_attr = {i: defaultdict(int) for i in TITLE_MAP.keys()}
    st.session_state.current_file_index = 0
    st.session_state.image_pairs = []
    st.session_state.current_pair_index = 0
    st.session_state.need_rerun = False
    st.session_state.initialized = False

def initialize_app():
    current_attr = st.session_state.current_file_index
    image_files = [os.path.join(IMAGE_FOLDER, f) for f in os.listdir(IMAGE_FOLDER)
                   if f.lower().endswith(('.jpg', '.png', '.jpeg'))]

    if not image_files:
        st.error("未找到任何图片。")
        st.stop()

    comparisons = st.session_state.image_counts_by_attr[current_attr]
    valid_pairs = [
        pair for pair in combinations(image_files, 2)
        if comparisons[pair[0]] < PER_IMAGE_MIN_COMPARISONS or comparisons[pair[1]] < PER_IMAGE_MIN_COMPARISONS
    ]

    if not valid_pairs:
        st.session_state.current_file_index += 1
        if st.session_state.current_file_index >= len(TITLE_MAP):
            st.success("所有感知维度的对比任务已完成，谢谢参与！")
            st.stop()
        else:
            initialize_app()
            return

    st.session_state.image_pairs = valid_pairs
    st.session_state.current_pair_index = 0
    st.session_state.initialized = True

def show_current_pair():
    if st.session_state.current_pair_index >= len(st.session_state.image_pairs):
        initialize_app()
        return False

    left_img, right_img = st.session_state.image_pairs[st.session_state.current_pair_index]
    current_attr = st.session_state.current_file_index

    st.title("街景图片对比评分系统")
    st.subheader(f"当前对比维度: {TITLE_MAP[current_attr]}")
    st.write(f"**进度**: {st.session_state.current_pair_index + 1}/{len(st.session_state.image_pairs)}")
    st.write(f"### {SELECT_TEXT_MAP[current_attr]}")

    col1, col2 = st.columns(2)
    try:
        with col1:
            st.image(Image.open(left_img), use_container_width=True, caption=f"左图: {os.path.basename(left_img)}")
            st.write(f"已比较次数: {st.session_state.image_counts_by_attr[current_attr][left_img]}")
        with col2:
            st.image(Image.open(right_img), use_container_width=True, caption=f"右图: {os.path.basename(right_img)}")
            st.write(f"已比较次数: {st.session_state.image_counts_by_attr[current_attr][right_img]}")
    except Exception as e:
        st.error(f"加载图片失败: {e}")
        st.session_state.current_pair_index += 1
        st.session_state.need_rerun = True
        return None

    return True

def record_selection(result):
    try:
        left_img, right_img = st.session_state.image_pairs[st.session_state.current_pair_index]
        current_attr = st.session_state.current_file_index

        if result == "left":
            st.session_state.ratings[left_img], st.session_state.ratings[right_img] = rate_1vs1(
                st.session_state.ratings[left_img], st.session_state.ratings[right_img])
        elif result == "right":
            st.session_state.ratings[right_img], st.session_state.ratings[left_img] = rate_1vs1(
                st.session_state.ratings[right_img], st.session_state.ratings[left_img])
        else:
            st.session_state.ratings[left_img], st.session_state.ratings[right_img] = rate_1vs1(
                st.session_state.ratings[left_img], st.session_state.ratings[right_img], drawn=True)

        st.session_state.image_counts_by_attr[current_attr][left_img] += 1
        st.session_state.image_counts_by_attr[current_attr][right_img] += 1

        output_file = f"comparison_results_{TITLE_MAP[current_attr]}.csv"
        if not os.path.exists(output_file):
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['User_ID', 'Left_Image', 'Right_Image', 'Result',
                                 'Left_Rating', 'Right_Rating'])

        with open(output_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                st.session_state.user_id,
                os.path.basename(left_img),
                os.path.basename(right_img),
                result,
                f"{st.session_state.ratings[left_img].mu:.3f}±{st.session_state.ratings[left_img].sigma:.3f}",
                f"{st.session_state.ratings[right_img].mu:.3f}±{st.session_state.ratings[right_img].sigma:.3f}"
            ])

        st.session_state.current_pair_index += 1
        if st.session_state.current_pair_index >= len(st.session_state.image_pairs):
            initialize_app()
        else:
            st.session_state.need_rerun = True

    except Exception as e:
        st.error(f"记录选择时出错: {str(e)}")

# 主程序逻辑
if not st.session_state.initialized:
    initialize_app()

if st.session_state.initialized:
    if show_current_pair():
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ 选择左侧", use_container_width=True):
                record_selection("left")
        with col2:
            if st.button("🟰 两者相当", use_container_width=True):
                record_selection("equal")
        with col3:
            if st.button("➡️ 选择右侧", use_container_width=True):
                record_selection("right")

if st.session_state.get("need_rerun", False):
    st.session_state.need_rerun = False
    st.rerun()
