import streamlit as st
import pandas as pd
import os

# --- 页面配置 ---
st.set_page_config(
    page_title="建筑设计规范 - 知识图谱标注工具",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 自定义 CSS 样式 ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        /* 调整表格字体大小 */
        .stDataFrame {
            font-size: 14px;
        }
        /* 顶部统计数据的样式 */
        .metric-box {
            background-color: #f0f2f6;
            border-radius: 5px;
            padding: 10px;
            text-align: center;
            margin-bottom: 10px;
        }
        .metric-label {
            font-size: 12px;
            color: #555;
        }
        .metric-value {
            font-size: 18px;
            font-weight: bold;
            color: #000;
        }
        /* 高亮搜索结果 */
        .highlight {
            background-color: yellow;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# --- 数据加载函数 ---
@st.cache_data
def load_data():
    """
    加载并解析CSV文件中的防火规范数据。
    """
    # 这是你提供的绝对路径
    file_path = r"E:\Users\czy\Desktop\标注工具V4.0项目\标注工具V4.0\设计规范集\GB 50016-2014(2018年版) 建筑设计防火规范.csv"
    
    # 初始化空的 DataFrame，以防文件读取失败
    df = pd.DataFrame(columns=["规范名称", "条文号", "条文内容"])

    if os.path.exists(file_path):
        try:
            # 尝试使用 utf-8 编码读取
            df = pd.read_csv(file_path, header=None, names=["规范名称", "条文号", "条文内容"], encoding='utf-8') 
        except UnicodeDecodeError:
            try:
                # 如果 utf-8 失败，尝试 gbk 编码（中文常用）
                df = pd.read_csv(file_path, header=None, names=["规范名称", "条文号", "条文内容"], encoding='gbk')
            except Exception as e:
                st.error(f"CSV编码错误，无法读取文件: {e}")
                return pd.DataFrame(columns=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
        except Exception as e:
            st.error(f"读取文件出错: {e}")
            return pd.DataFrame(columns=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
    else:
        # 如果文件路径不存在，给出警告并返回空表
        st.error(f"未找到文件: {file_path}。请确认文件路径是否正确。")
        return pd.DataFrame(columns=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
    
    if df.empty:
        st.warning("文件内容为空。")
        return pd.DataFrame(columns=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])

    # 增加模拟的标注状态列
    # 注意：这里我们保留了原本的模拟标注逻辑，以便你在界面上能看到效果。
    # 实际项目中，这些状态应该从数据库或另一个标注文件中读取。
    df["id"] = range(1, len(df) + 1)
    df["实体标注"] = ""
    df["关系标注"] = ""
    df["规则标注"] = ""
    
    # 随机给一些行加上已标注的状态，为了演示效果
    for index, row in df.iterrows():
        if index % 3 == 0:
            df.at[index, "实体标注"] = "√"
            df.at[index, "关系标注"] = "√"
        if index % 5 == 0:
             df.at[index, "规则标注"] = "√"

    # 为了匹配后续列名，进行重命名
    df.rename(columns={"规范名称": "规范", "条文号": "条文"}, inplace=True)

    # 重排下列顺序
    cols = ["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"]
    
    # 确保只返回这些列
    return df[cols]

df = load_data()

# --- 顶部标题 ---
st.title("Code Knowledge Graph Label Toolkit V4.1 - 建筑设计防火规范全集")
st.markdown("---")

# --- 工具栏区域 (Toolbar) ---
col_search, col_actions, col_stats = st.columns([3, 4, 3], gap="medium")

# 1. 左侧：条文定位与查找
with col_search:
    st.subheader("条文定位 & 查找")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        filter_option = st.radio("显示模式", ["显示全部", "只示已处理", "只示未处理"], index=0, key="filter_mode")
    
    with c2:
        search_query = st.text_input("输入查找内容", placeholder="例如：甲类厂房")
    
    with c3:
        st.write("") # Spacer
        st.write("") # Spacer
        if st.button("查找", use_container_width=True):
            if search_query:
                st.success(f"正在搜索: {search_query}")
            else:
                st.warning("请输入搜索关键词")

# 2. 中间：条文操作与建模
with col_actions:
    st.subheader("条文操作")
    ac1, ac2, ac3, ac4 = st.columns(4)
    with ac1:
        st.button("删除\n条文", use_container_width=True)
        st.button("修改\n序号", use_container_width=True)
    with ac2:
        st.button("插入\n条文", use_container_width=True)
        st.button("拆解\n条文", use_container_width=True)
    with ac3:
        st.button("图谱\n建模", type="primary", use_container_width=True, help="核心功能：生成知识图谱")
        st.button("重新\n建模", use_container_width=True)
    with ac4:
        st.button("标注\n规则", type="primary", use_container_width=True)
        st.button("重写\n规则", use_container_width=True)

# 3. 右侧：标注统计
with col_stats:
    st.subheader("标注统计")
    stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)
    
    total_items = len(df)
    if not df.empty:
        labeled_entities = len(df[df["实体标注"] == "√"])
        labeled_relations = len(df[df["关系标注"] == "√"])
        labeled_rules = len(df[df["规则标注"] == "√"])
    else:
        labeled_entities = 0
        labeled_relations = 0
        labeled_rules = 0

    def render_stat(label, value):
        return f"""
        <div class="metric-box">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """
    
    with stat_c1:
        st.markdown(render_stat("总条文", total_items), unsafe_allow_html=True)
    with stat_c2:
        st.markdown(render_stat("已标注实体", labeled_entities), unsafe_allow_html=True)
    with stat_c3:
        st.markdown(render_stat("已标注关系", labeled_relations), unsafe_allow_html=True)
    with stat_c4:
        st.markdown(render_stat("已处理规则", labeled_rules), unsafe_allow_html=True)

st.markdown("---")

# --- 数据处理逻辑 ---
if not df.empty:
    display_df = df.copy()

    # 过滤逻辑
    if filter_option == "只示已处理":
        display_df = display_df[display_df["规则标注"] == "√"]
    elif filter_option == "只示未处理":
        display_df = display_df[display_df["规则标注"] != "√"]

    # 搜索逻辑
    if search_query:
        # 使用 astype(str) 防止非字符串列报错
        display_df = display_df[
            display_df["条文内容"].astype(str).str.contains(search_query) | 
            display_df["条文"].astype(str).str.contains(search_query)
        ]
else:
    # 如果数据为空，显示空表结构
    display_df = pd.DataFrame(columns=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])

# --- 主数据表格 ---
column_config = {
    "id": st.column_config.NumberColumn("ID", width="small"),
    "规范": st.column_config.TextColumn("规范名称", width="medium"),
    "条文": st.column_config.TextColumn("条文号", width="small"),
    "条文内容": st.column_config.TextColumn("条文内容", width="large"),
    "实体标注": st.column_config.TextColumn("实体", width="small"),
    "关系标注": st.column_config.TextColumn("关系", width="small"),
    "规则标注": st.column_config.TextColumn("规则", width="small"),
}

st.data_editor(
    display_df,
    column_config=column_config,
    use_container_width=True,
    hide_index=True,
    height=800, # 增加高度以展示更多数据
    disabled=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"]
)

# --- 底部状态栏 ---
st.caption(f"当前共加载 {len(display_df)} 条数据 | 系统状态: 就绪 | 数据来源: GB 50016-2014(2018年版) 建筑设计防火规范.csv")