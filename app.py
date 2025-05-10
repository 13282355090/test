import streamlit as st
import os
import csv
from collections import defaultdict
from trueskill import Rating, rate_1vs1
import pandas as pd
from PIL import Image

# 配置路径
IMAGE_FOLDER = "image"
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

# 管理员登录区块
st.sidebar.subheader("管理员登录")
admin_password = st.sidebar.text_input("请输入管理员密码", type="password")

if admin_password == "2023202090005":
    st.sidebar.success("身份验证成功")
    st.success("密码正确，请点击下方按钮下载结果文件：")

    if os.path.exists(COUNT_CSV):
        with open(COUNT_CSV, "rb") as f:
            st.download_button(
                label="📊 下载图片比较次数统计",
                data=f,
                file_name="image_comparison_counts.csv",
                mime="text/csv"
            )

    st.stop()

# 初始化 session state
if 'initialized' not in st.session_state:
    st.session_state.ratings = defaultdict(lambda: Rating())
    st.session_state.comparison_counts = defaultdict(int)
    st.session_state.image_pairs = []
    st.session_state.current_pair_index = 0
    st.session_state.initialized = False
    st.session_state.need_rerun = False
    st.session_state.current_file_index = 0

# 每个对比计划的标题映射
TITLE_MAP = {
    0: "美丽",
    1: "无聊",
    2: "压抑",
    3: "活力",
    4: "安全",
    5: "财富"
}

def initialize_app():
    try:
        current_file = PAIRS_FILES[st.session_state.current_file_index]
        st.session_state.image_pairs = []
        with open(current_file, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) >= 2:
                    left_img = os.path.join(IMAGE_FOLDER, row[0].strip())
                    right_img = os.path.join(IMAGE_FOLDER, row[1].strip())
                    if os.path.exists(left_img) and os.path.exists(right_img):
                        st.session_state.image_pairs.append((left_img, right_img))

        if not st.session_state.image_pairs:
            st.error("没有有效的图片对比对！")
            st.stop()

        # 根据当前文件生成对应的输出文件
        current_file = PAIRS_FILES[st.session_state.current_file_index]
        output_file = OUTPUT_FILES[current_file]
        if not os.path.exists(output_file):
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Left_Image', 'Right_Image', 'Result', 'Left_Rating', 'Right_Rating'])

        st.session_state.initialized = True

    except Exception as e:
        st.error(f"初始化失败: {str(e)}")
        st.stop()

def remove_current_pair_from_csv():
    try:
        current_pair = st.session_state.image_pairs[st.session_state.current_pair_index]
        left_basename = os.path.basename(current_pair[0])
        right_basename = os.path.basename(current_pair[1])

        current_file = PAIRS_FILES[st.session_state.current_file_index]
        updated_rows = []
        with open(current_file, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if len(row) >= 2 and not (
                    row[0].strip() == left_basename and row[1].strip() == right_basename
                ):
                    updated_rows.append(row)

        with open(current_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(updated_rows)

    except Exception as e:
        st.warning(f"删除当前对比项失败：{e}")

def show_current_pair():
    if st.session_state.current_pair_index >= len(st.session_state.image_pairs):
        st.success(f"🎉 所有图片对比已完成！")
        st.session_state.current_file_index += 1
        if st.session_state.current_file_index < len(PAIRS_FILES):
            st.session_state.current_pair_index = 0
            initialize_app()  # 重新加载新的对比文件
            return False
        else:
            st.success("所有对比计划已完成！")
            return False

    left_img, right_img = st.session_state.image_pairs[st.session_state.current_pair_index]
    # 根据当前文件更新标题
    st.title("街景图片对比评分系统")
    st.subheader(f"当前对比计划: {TITLE_MAP[st.session_state.current_file_index]}")  # 显示当前计划的标题
    st.write(f"**进度**: {st.session_state.current_pair_index + 1}/{len(st.session_state.image_pairs)}")
    col1, col2 = st.columns(2)

    try:
        with col1:
            st.image(Image.open(left_img), use_container_width=True, caption=f"左图: {os.path.basename(left_img)}")
            st.write(f"已比较次数: {st.session_state.comparison_counts[left_img]}")
        with col2:
            st.image(Image.open(right_img), use_container_width=True, caption=f"右图: {os.path.basename(right_img)}")
            st.write(f"已比较次数: {st.session_state.comparison_counts[right_img]}")
        st.write("### 请选择哪张图片让你感到更加安全:")
    except Exception as e:
        st.error(f"加载图片失败: {str(e)}")
        st.session_state.current_pair_index += 1
        st.session_state.need_rerun = True
        return None

    return True

def record_selection(result):
    try:
        left_img, right_img = st.session_state.image_pairs[st.session_state.current_pair_index]

        # 更新评分
        if result == "left":
            st.session_state.ratings[left_img], st.session_state.ratings[right_img] = rate_1vs1(
                st.session_state.ratings[left_img], st.session_state.ratings[right_img], drawn=False)
        elif result == "right":
            st.session_state.ratings[right_img], st.session_state.ratings[left_img] = rate_1vs1(
                st.session_state.ratings[right_img], st.session_state.ratings[left_img], drawn=False)
        else:
            st.session_state.ratings[left_img], st.session_state.ratings[right_img] = rate_1vs1(
                st.session_state.ratings[left_img], st.session_state.ratings[right_img], drawn=True)

        # 更新比较次数
        st.session_state.comparison_counts[left_img] += 1
        st.session_state.comparison_counts[right_img] += 1

        # 写入结果
        current_file = PAIRS_FILES[st.session_state.current_file_index]
        output_file = OUTPUT_FILES[current_file]
        with open(output_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                os.path.basename(left_img),
                os.path.basename(right_img),
                result,
                f"{st.session_state.ratings[left_img].mu:.3f}±{st.session_state.ratings[left_img].sigma:.3f}",
                f"{st.session_state.ratings[right_img].mu:.3f}±{st.session_state.ratings[right_img].sigma:.3f}"
            ])
            f.flush()

        # 删除当前项并刷新数据
        remove_current_pair_from_csv()
        st.session_state.current_pair_index += 1
        initialize_app()
        st.session_state.need_rerun = True

    except Exception as e:
        st.error(f"记录选择时出错: {str(e)}")

# 页面主内容
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

# 触发 rerun
if st.session_state.get("need_rerun", False):
    st.session_state.need_rerun = False
    st.rerun()
