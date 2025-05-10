import streamlit as st
import uuid
import csv
from collections import defaultdict
from trueskill import Rating, rate_1vs1
from PIL import Image
from streamlit_cookies_manager import Cookies

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

# 使用 cookies 管理用户标识符
cookies = Cookies(st)

# 检查是否已有用户唯一标识符
if 'user_id' not in cookies:
    # 如果没有，生成一个新的 UUID 并存入 cookies
    user_id = str(uuid.uuid4())  # 生成唯一的 UUID
    cookies['user_id'] = user_id
    cookies.save()  # 保存 Cookie
else:
    # 如果已有，则读取存储的 user_id
    user_id = cookies['user_id']

# 显示当前用户 ID（可用于调试）
st.write(f"当前用户 ID: {user_id}")

# 其余应用代码...
def initialize_app():
    while st.session_state.current_file_index < len(PAIRS_FILES):
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

        if st.session_state.image_pairs:
            output_file = OUTPUT_FILES[current_file]
            if not os.path.exists(output_file):
                with open(output_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Left_Image', 'Right_Image', 'Result', 'Left_Rating', 'Right_Rating'])
            st.session_state.initialized = True
            return

        else:
            st.session_state.current_file_index += 1

    st.success("所有对比计划已完成！")
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
        st.session_state.current_file_index += 1
        st.session_state.initialized = False
        initialize_app()
        return False

    left_img, right_img = st.session_state.image_pairs[st.session_state.current_pair_index]
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
        st.session_state.current_pair_index += 1
        st.session_state.need_rerun = True
        return None

    return True

def record_selection(result):
    try:
        left_img, right_img = st.session_state.image_pairs[st.session_state.current_pair_index]

        if result == "left":
            st.session_state.ratings[left_img], st.session_state.ratings[right_img] = rate_1vs1(
                st.session_state.ratings[left_img], st.session_state.ratings[right_img], drawn=False)
        elif result == "right":
            st.session_state.ratings[right_img], st.session_state.ratings[left_img] = rate_1vs1(
                st.session_state.ratings[right_img], st.session_state.ratings[left_img], drawn=False)
        else:
            st.session_state.ratings[left_img], st.session_state.ratings[right_img] = rate_1vs1(
                st.session_state.ratings[left_img], st.session_state.ratings[right_img], drawn=True)

        st.session_state.comparison_counts[left_img] += 1
        st.session_state.comparison_counts[right_img] += 1

        current_file = PAIRS_FILES[st.session_state.current_file_index]
        output_file = OUTPUT_FILES[current_file]
        with open(output_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                os.path.basename(left_img),
                os.path.basename(right_img),
                result,
                f"{st.session_state.ratings[left_img].mu:.3f}±{st.session_state.ratings[left_img].sigma:.3f}",
                f"{st.session_state.ratings[right_img].mu:.3f}±{st.session_state.ratings[right_img].sigma:.3f}",
                user_id  # 使用 cookies 保存的 user_id
            ])

        remove_current_pair_from_csv()
        st.session_state.current_pair_index += 1
        st.session_state.need_rerun = True

    except Exception as e:
        st.error(f"记录选择时出错: {str(e)}")

# 主逻辑
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
