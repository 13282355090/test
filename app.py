import streamlit as st
import os
import csv
import random
from collections import defaultdict
from trueskill import Rating, rate_1vs1
from PIL import Image

# 配置路径
IMAGE_FOLDER = "images"
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
    st.session_state.image_list = [
        os.path.join(IMAGE_FOLDER, img) for img in os.listdir(IMAGE_FOLDER)
        if img.lower().endswith(('.jpg', '.jpeg', '.png')) and os.path.isfile(os.path.join(IMAGE_FOLDER, img))
    ]
    st.session_state.comparison_counts = defaultdict(int)
    st.session_state.ratings = defaultdict(lambda: Rating())
    st.session_state.need_rerun = False

# 随机加权选择图片对
def weighted_random_pair():
    images = st.session_state.image_list
    counts = st.session_state.comparison_counts

    # 计算每张图片的权重（出现次数越少，权重越高）
    weights = [1 / (1 + counts[img]) for img in images]

    # 抽取两张不重复的图片
    selected = random.choices(images, weights=weights, k=2)
    while selected[0] == selected[1]:
        selected = random.choices(images, weights=weights, k=2)
    return selected[0], selected[1]

# 显示当前图片对
def show_current_pair():
    left_img, right_img = weighted_random_pair()
    st.session_state.current_pair = (left_img, right_img)

    st.title("街景图片对比评分系统")
    st.subheader("当前对比任务（随机）")
    st.write("请选择更符合主题的图片（主题在设计时自定义）：")

    col1, col2 = st.columns(2)
    with col1:
        st.image(Image.open(left_img), use_container_width=True, caption=f"左图: {os.path.basename(left_img)}")
        st.write(f"已比较次数: {st.session_state.comparison_counts[left_img]}")
    with col2:
        st.image(Image.open(right_img), use_container_width=True, caption=f"右图: {os.path.basename(right_img)}")
        st.write(f"已比较次数: {st.session_state.comparison_counts[right_img]}")

# 记录选择
def record_selection(result):
    try:
        left_img, right_img = st.session_state.current_pair

        if result == "left":
            st.session_state.ratings[left_img], st.session_state.ratings[right_img] = rate_1vs1(
                st.session_state.ratings[left_img], st.session_state.ratings[right_img])
        elif result == "right":
            st.session_state.ratings[right_img], st.session_state.ratings[left_img] = rate_1vs1(
                st.session_state.ratings[right_img], st.session_state.ratings[left_img])
        else:
            st.session_state.ratings[left_img], st.session_state.ratings[right_img] = rate_1vs1(
                st.session_state.ratings[left_img], st.session_state.ratings[right_img], drawn=True)

        st.session_state.comparison_counts[left_img] += 1
        st.session_state.comparison_counts[right_img] += 1

        # 记录结果到总文件
        with open("comparison_log.csv", 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                st.session_state.user_id,
                os.path.basename(left_img),
                os.path.basename(right_img),
                result,
                f"{st.session_state.ratings[left_img].mu:.3f}±{st.session_state.ratings[left_img].sigma:.3f}",
                f"{st.session_state.ratings[right_img].mu:.3f}±{st.session_state.ratings[right_img].sigma:.3f}"
            ])

        st.rerun()

    except Exception as e:
        st.error(f"记录选择时出错: {str(e)}")

# 主逻辑
if st.session_state.need_rerun:
    st.session_state.need_rerun = False
    show_current_pair()

if not st.session_state.need_rerun:
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
