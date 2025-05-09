
# app_streamlit_downloadable.py
import streamlit as st
import os
import csv
from collections import defaultdict
from trueskill import Rating, rate_1vs1
import pandas as pd
from PIL import Image

# 配置路径
IMAGE_FOLDER = "image"
PAIRS_CSV = "comparison_pairs.csv"
OUTPUT_CSV = "comparison_results.csv"
COUNT_CSV = "image_comparison_counts.csv"

# 初始化状态
if 'initialized' not in st.session_state:
    st.session_state.ratings = defaultdict(lambda: Rating())
    st.session_state.comparison_counts = defaultdict(int)
    st.session_state.image_pairs = []
    st.session_state.current_pair_index = 0
    st.session_state.initialized = False

def initialize_app():
    try:
        if not os.path.exists(IMAGE_FOLDER):
            st.error(f"图片文件夹 {IMAGE_FOLDER} 不存在！")
            st.stop()

        if not os.path.exists(PAIRS_CSV):
            st.error(f"比较对文件 {PAIRS_CSV} 不存在！")
            st.stop()

        st.session_state.image_pairs = []
        with open(PAIRS_CSV, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) >= 2:
                    left_img = os.path.join(IMAGE_FOLDER, row[0].strip())
                    right_img = os.path.join(IMAGE_FOLDER, row[1].strip())
                    if not os.path.exists(left_img) or not os.path.exists(right_img):
                        continue
                    st.session_state.image_pairs.append((left_img, right_img))
                    st.session_state.comparison_counts[left_img] += 1
                    st.session_state.comparison_counts[right_img] += 1

        if not st.session_state.image_pairs:
            st.error("没有有效的图片对比对！")
            st.stop()

        if not os.path.exists(OUTPUT_CSV):
            with open(OUTPUT_CSV, 'w', newline='') as f:
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

        updated_rows = []
        with open(PAIRS_CSV, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if len(row) >= 2 and not (
                    row[0].strip() == left_basename and row[1].strip() == right_basename
                ):
                    updated_rows.append(row)

        with open(PAIRS_CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(updated_rows)

    except Exception as e:
        st.warning(f"删除当前对比项失败：{e}")

def show_current_pair():
    if st.session_state.current_pair_index >= len(st.session_state.image_pairs):
        st.success("🎉 所有图片对比已完成！")
        try:
            count_data = []
            for img, count in st.session_state.comparison_counts.items():
                count_data.append({
                    'Image': os.path.basename(img),
                    'Comparison_Count': count
                })
            pd.DataFrame(count_data).to_csv(COUNT_CSV, index=False)

            with open(OUTPUT_CSV, "rb") as f:
                st.download_button(
                    label="下载比较结果",
                    data=f,
                    file_name="comparison_results.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"保存结果失败: {str(e)}")
        return False

    left_img, right_img = st.session_state.image_pairs[st.session_state.current_pair_index]
    st.write(f"**进度**: {st.session_state.current_pair_index + 1}/{len(st.session_state.image_pairs)}")
    col1, col2 = st.columns(2)

    try:
        with col1:
            st.image(Image.open(left_img), use_column_width=True, caption=f"左图: {os.path.basename(left_img)}")
            st.write(f"比较次数: {st.session_state.comparison_counts[left_img]}")
        with col2:
            st.image(Image.open(right_img), use_column_width=True, caption=f"右图: {os.path.basename(right_img)}")
            st.write(f"比较次数: {st.session_state.comparison_counts[right_img]}")
        st.write("### 请选择哪张图片让你感到更加安全:")
    except Exception as e:
        st.error(f"加载图片失败: {str(e)}")
        st.session_state.current_pair_index += 1
        st.rerun()
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

        with open(OUTPUT_CSV, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                os.path.basename(left_img),
                os.path.basename(right_img),
                result,
                f"{st.session_state.ratings[left_img].mu:.3f}±{st.session_state.ratings[left_img].sigma:.3f}",
                f"{st.session_state.ratings[right_img].mu:.3f}±{st.session_state.ratings[right_img].sigma:.3f}"
            ])
            f.flush()

        remove_current_pair_from_csv()
        st.session_state.current_pair_index += 1

    except Exception as e:
        st.error(f"记录选择时出错: {str(e)}")

    st.rerun()

# 页面主内容
st.title("🏙️ 街景图片对比评分系统")
st.markdown("请选择哪张图片让你感到更加安全")

# 用户手动下载 CSV 文件（只要存在）
if os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, "rb") as f:
        st.download_button(
            label="📥 下载对比结果 CSV",
            data=f,
            file_name="comparison_results.csv",
            mime="text/csv"
        )

if os.path.exists(COUNT_CSV):
    with open(COUNT_CSV, "rb") as f:
        st.download_button(
            label="📊 下载图片比较次数统计",
            data=f,
            file_name="image_comparison_counts.csv",
            mime="text/csv"
        )

if not st.session_state.initialized:
    initialize_app()

if st.session_state.initialized:
    if show_current_pair():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("⬅️ 选择左侧", on_click=record_selection, args=("left",), use_container_width=True)
        with col2:
            st.button("🟰 两者相当", on_click=record_selection, args=("equal",), use_container_width=True)
        with col3:
            st.button("➡️ 选择右侧", on_click=record_selection, args=("right",), use_container_width=True)
