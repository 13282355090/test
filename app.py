import streamlit as st
import os
import random
import csv
from collections import defaultdict
from trueskill import Rating, rate_1vs1
from PIL import Image

# 文件与路径配置
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
    st.success("密码正确，请点击下方按钮下载所有结果文件：")

    if os.path.exists(COUNT_CSV):
        with open(COUNT_CSV, "rb") as f:
            bytes_data = f.read()
            st.download_button("📊 下载图片比较次数统计", data=bytes_data, file_name=COUNT_CSV, mime="text/csv")

    for input_file, output_file in OUTPUT_FILES.items():
        if os.path.exists(output_file):
            with open(output_file, "rb") as f:
                file_bytes = f.read()
                label_name = output_file.replace("comparison_results_", "").replace(".csv", "")
                st.download_button(f"⬇️ 下载 {label_name} 结果文件", data=file_bytes, file_name=output_file, mime="text/csv")
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
    st.session_state.current_file_index = 0
    st.session_state.initialized = False
    st.session_state.need_rerun = False

def update_comparison_counts():
    with open(COUNT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Image', 'Comparison_Count'])
        for img, count in st.session_state.comparison_counts.items():
            writer.writerow([img, count])

def load_comparison_counts(image_files):
    if os.path.exists(COUNT_CSV):
        with open(COUNT_CSV, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) == 2:
                    st.session_state.comparison_counts[row[0]] = int(row[1])
    else:
        for img in image_files:
            st.session_state.comparison_counts[img] = 0
        update_comparison_counts()

def initialize_app():
    while st.session_state.current_file_index < len(PAIRS_FILES):
        image_files = [img for img in os.listdir(IMAGE_FOLDER)
                       if img.lower().endswith(('.jpg', '.png', '.jpeg'))]

        if len(image_files) < 2:
            st.error("图片数量不足，至少需要2张图片。")
            st.stop()

        st.session_state.all_images = image_files

        # 初始化或读取计数
        load_comparison_counts(image_files)

        # 检查是否还有图片对比次数不足
        incomplete_images = [img for img in image_files if st.session_state.comparison_counts[img] < 4]
        if len(incomplete_images) >= 2:
            # 初始化结果文件
            current_file = PAIRS_FILES[st.session_state.current_file_index]
            if not os.path.exists(OUTPUT_FILES[current_file]):
                with open(OUTPUT_FILES[current_file], 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['User_ID', 'Left_Image', 'Right_Image', 'Result',
                                     'Left_Rating', 'Right_Rating'])
            st.session_state.initialized = True
            return
        else:
            # 当前感知维度已完成，进入下一维度
            st.session_state.current_file_index += 1
            continue

    st.success("所有对比计划已完成！")
    st.stop()

def get_next_pair():
    counts = st.session_state.comparison_counts
    available = [img for img in st.session_state.all_images if counts[img] < 4]

    if len(available) < 2:
        # 不在这里跳维度，交由 initialize_app 控制
        return None, None

    weights = [4 - counts[img] for img in available]
    chosen = random.choices(available, weights=weights, k=2)
    while chosen[0] == chosen[1]:
        chosen = random.choices(available, weights=weights, k=2)

    counts[chosen[0]] += 1
    counts[chosen[1]] += 1
    update_comparison_counts()

    return os.path.join(IMAGE_FOLDER, chosen[0]), os.path.join(IMAGE_FOLDER, chosen[1])

def show_current_pair(left_img, right_img):
    st.title("街景图片对比评分系统")
    index = st.session_state.current_file_index
    st.subheader(f"当前对比计划: {TITLE_MAP[index]}")
    st.write(f"### {SELECT_TEXT_MAP[index]}")

    col1, col2 = st.columns(2)
    try:
        with col1:
            st.image(Image.open(left_img), use_container_width=True, caption=f"左图: {os.path.basename(left_img)}")
            st.write(f"已比较次数: {st.session_state.comparison_counts[os.path.basename(left_img)]}")
        with col2:
            st.image(Image.open(right_img), use_container_width=True, caption=f"右图: {os.path.basename(right_img)}")
            st.write(f"已比较次数: {st.session_state.comparison_counts[os.path.basename(right_img)]}")
    except Exception as e:
        st.error(f"加载图片失败: {str(e)}")
        st.session_state.need_rerun = True
        return False
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

        current_file = PAIRS_FILES[st.session_state.current_file_index]
        output_file = OUTPUT_FILES[current_file]
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
        st.session_state.need_rerun = True
    except Exception as e:
        st.error(f"记录选择时出错: {str(e)}")

# 主逻辑执行
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
