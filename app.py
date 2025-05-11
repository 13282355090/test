import streamlit as st
import os
import random
from collections import defaultdict
from trueskill import Rating, rate_1vs1
from PIL import Image

# 配置路径
IMAGE_FOLDER = "images"
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
    st.session_state.images = []
    st.session_state.current_pair = None
    st.session_state.need_rerun = False

# 加载所有图片
def load_images():
    image_files = [f for f in os.listdir(IMAGE_FOLDER) if f.endswith(('.jpg', '.png', '.jpeg'))]
    st.session_state.images = [os.path.join(IMAGE_FOLDER, img) for img in image_files]

# 根据对比次数调整图片出现概率
def select_images():
    weights = [1 / (st.session_state.comparison_counts[img] + 1) for img in st.session_state.images]
    total_weight = sum(weights)
    normalized_weights = [weight / total_weight for weight in weights]
    selected_images = random.choices(st.session_state.images, normalized_weights, k=2)
    return selected_images

# 主逻辑
def initialize_app():
    load_images()
    st.session_state.initialized = True

def show_current_pair():
    # 随机选择两张图片进行对比
    left_img, right_img = select_images()
    st.session_state.current_pair = (left_img, right_img)
    
    # 显示图片
    st.title("街景图片对比评分系统")
    st.write(f"**进度**: {len(st.session_state.comparison_counts)} 对比")
    st.write(f"### 请选择你更偏向的图片:")

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

def record_selection(result):
    try:
        left_img, right_img = st.session_state.current_pair

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

        # 保存选择结果到文件
        with open(COUNT_CSV, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([st.session_state.user_id, os.path.basename(left_img), os.path.basename(right_img), result])

        st.session_state.need_rerun = True

    except Exception as e:
        st.error(f"记录选择时出错: {str(e)}")

# 初始化应用
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
