
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import zipfile
from io import BytesIO, StringIO
import os
import networkx as nx
from pyvis.network import Network
import json
import re
from typing import Dict, List, Tuple
import csv


# ==================== 页面配置 ====================
st.set_page_config(
    page_title="建筑设计规范 - 知识图谱标注工具",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自定义样式 ====================
def load_custom_css():
    """加载自定义 CSS，全局高端简洁风格"""
    st.markdown(
        """
        <style>
        /* 隐藏默认菜单和页脚 */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* 全局背景与字体 */
        body {
            background-color: #f5f7fb;
            color: #111827;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .block-container {
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        h1, h2, h3, h4 {
            font-weight: 600;
            letter-spacing: 0.02em;
            color: #111827;
        }

        /* 卡片样式容器 */
        .card {
            background-color: #ffffff;
            padding: 1.25rem 1.5rem;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
        }

        /* 细分标题下的小横线 */
        .section-title {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        .section-subtitle {
            font-size: 0.85rem;
            color: #6b7280;
            margin-bottom: 0.75rem;
        }

        /* 按钮统一样式 */
        .stButton > button {
            border-radius: 8px;
            border: 1px solid #d1d5db;
            background: #ffffff;
            color: #111827;
            padding: 0.45rem 0.75rem;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.15s ease-in-out;
        }

        .stButton > button:hover {
            border-color: #111827;
            background: #f9fafb;
        }

        .stButton > button:focus {
            outline: none;
            border-color: #111827;
            box-shadow: 0 0 0 1px #11182711;
        }

        /* 模拟“主按钮”风格（通过容器 class 来区分） */
        .primary-button > button {
            background: linear-gradient(135deg, #111827, #1f2937);
            color: white !important;
            border-color: transparent;
        }

        .primary-button > button:hover {
            background: #111827;
        }

        /* 侧边栏风格 */
        [data-testid="stSidebar"] {
            background-color: #0f172a;
            color: #e5e7eb;
        }

        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3 {
            color: #e5e7eb;
        }

        /* 侧边栏按钮 */
        [data-testid="stSidebar"] .stButton > button {
            background: #111827;
            color: #e5e7eb;
            border: 1px solid #1f2937;
        }

        [data-testid="stSidebar"] .stButton > button:hover {
            background: #1f2937;
        }

        /* metric 样式微调 */
        [data-testid="stMetricLabel"] {
            color: #6b7280;
        }

        /* 表格微调 */
        .dataframe {
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ==================== Session State 初始化 ====================
def init_session_state():
    """初始化所有会话状态变量"""
    defaults = {
        'projects': {},
        'current_project': None,
        'current_project_path': None,
        'df': pd.DataFrame(columns=["规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"]),
        'knowledge_graph': {'nodes': [], 'edges': []},
        'current_view': 'main',
        # 弹窗控制
        'show_import_modal': False,
        'show_new_project_modal': False,
        'show_load_project_modal': False,
        'show_ontology_modal': False,
        # 导入相关
        'import_preview_df': None,
        'import_step': 1,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ==================== 项目管理函数 ====================
def create_new_project(project_name: str) -> tuple:
    """创建新项目"""
    if not project_name:
        return False, "项目名称不能为空"
    
    if project_name in st.session_state.projects:
        return False, f"项目 '{project_name}' 已存在"
    
    project_data = {
        'name': project_name,
        'created_at': datetime.now().isoformat(),
        'data': [],
        'ontology': {'nodes': [], 'edges': []}
    }
    
    st.session_state.projects[project_name] = project_data
    st.session_state.current_project = project_name
    st.session_state.df = pd.DataFrame(columns=["规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
    st.session_state.knowledge_graph = {'nodes': [], 'edges': []}
    
    return True, f"✅ 项目 '{project_name}' 创建成功！"

def load_project(project_name: str) -> bool:
    """加载项目"""
    if project_name not in st.session_state.projects:
        return False
    
    project_data = st.session_state.projects[project_name]
    st.session_state.current_project = project_name
    
    if project_data.get('data'):
        st.session_state.df = pd.DataFrame(project_data['data'])
    else:
        st.session_state.df = pd.DataFrame(columns=["规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
    
    st.session_state.knowledge_graph = project_data.get('ontology', {'nodes': [], 'edges': []})
    return True

def save_current_project():
    """保存当前项目"""
    if st.session_state.current_project:
        project_name = st.session_state.current_project
        st.session_state.projects[project_name]['data'] = st.session_state.df.to_dict('records')
        st.session_state.projects[project_name]['ontology'] = st.session_state.knowledge_graph

def export_project():
    """导出当前项目为ZIP"""
    if not st.session_state.current_project:
        st.warning("⚠️ 请先选择一个项目")
        return
    
    save_current_project()
    project_name = st.session_state.current_project
    project_data = st.session_state.projects[project_name]
    
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('project.json', json.dumps(project_data, ensure_ascii=False, indent=2))
        if not st.session_state.df.empty:
            zf.writestr('data.csv', st.session_state.df.to_csv(index=False, encoding='utf-8-sig'))
        zf.writestr('ontology.json', json.dumps(st.session_state.knowledge_graph, ensure_ascii=False, indent=2))
    
    zip_buffer.seek(0)
    st.download_button(
        label="⬇️ 点击下载项目包",
        data=zip_buffer,
        file_name=f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        mime="application/zip",
        type="primary"
    )

# ==================== 智能列识别函数 ====================
def guess_column_mapping(columns: list) -> dict:
    """
    智能猜测列映射关系
    根据列名关键字自动匹配到: 规范、条文、条文内容
    """
    mapping = {
        '规范': None,
        '条文': None,
        '条文内容': None
    }
    
    # 定义关键字匹配规则（优先级从高到低）
    rules = {
        '规范': ['规范名称', '规范', '标准名称', '标准', 'standard', 'spec', '文件名'],
        '条文': ['条文号', '条文编号', '章节号', '编号', '条款号', 'article', 'clause', 'section', '序号'],
        '条文内容': ['条文内容', '内容', '正文', '条款内容', 'content', 'text', '描述', '说明']
    }
    
    columns_lower = [str(c).lower().strip() for c in columns]
    
    for target, keywords in rules.items():
        for keyword in keywords:
            for i, col in enumerate(columns_lower):
                if keyword.lower() in col and mapping[target] is None:
                    mapping[target] = columns[i]
                    break
            if mapping[target]:
                break
    
    # 如果还有未匹配的，按列顺序自动分配
    unmapped_cols = [c for c in columns if c not in mapping.values()]
    unmapped_targets = [t for t, v in mapping.items() if v is None]
    
    for i, target in enumerate(unmapped_targets):
        if i < len(unmapped_cols):
            mapping[target] = unmapped_cols[i]
    
    return mapping

def read_file_with_encoding(uploaded_file) -> pd.DataFrame:
    """尝试多种编码读取文件"""
    content = uploaded_file.getvalue()
    
    # 尝试的编码列表
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1']
    
    for encoding in encodings:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(BytesIO(content), encoding=encoding)
            elif uploaded_file.name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(BytesIO(content))
            else:
                df = pd.read_csv(BytesIO(content), encoding=encoding)
            
            # 检查是否读取成功（至少有1列和1行）
            if len(df.columns) >= 1 and len(df) >= 1:
                return df
        except Exception:
            continue
    
    raise ValueError("无法识别文件编码，请检查文件格式")

def apply_column_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """
    应用列映射，生成标准格式的DataFrame
    """
    result_df = pd.DataFrame()
    
    for target_col, source_col in mapping.items():
        if source_col and source_col in df.columns:
            result_df[target_col] = df[source_col].astype(str).fillna('')
        else:
            result_df[target_col] = ''
    
    # 添加标注列
    result_df['实体标注'] = False
    result_df['关系标注'] = False
    result_df['规则标注'] = False
    
    return result_df

# ==================== 导入弹窗（核心优化） ====================
def show_import_modal():
    """导入规范弹窗 - 支持任意3列CSV自动映射"""
    if not st.session_state.show_import_modal:
        return
    
    with st.expander("📥 智能导入数据", expanded=True):
        st.markdown("### 📄 上传文件")
        st.info("💡 支持任意格式的CSV/Excel文件，系统会自动识别并映射列")
        
        uploaded_file = st.file_uploader(
            "选择文件",
            type=['csv', 'xlsx', 'xls'],
            key="smart_uploader",
            help="支持CSV、Excel格式，任意列名都可以"
        )
        
        if uploaded_file:
            try:
                # 读取文件
                df = read_file_with_encoding(uploaded_file)
                st.success(f"✅ 文件读取成功！共 {len(df)} 行, {len(df.columns)} 列")
                
                # 显示原始数据预览
                with st.expander("📋 原始数据预览（前5行）", expanded=False):
                    st.dataframe(df.head(), use_container_width=True)
                
                st.markdown("---")
                st.markdown("### 🔄 列映射配置")
                st.caption("系统已自动识别列，您也可以手动调整映射关系")
                
                # 智能猜测映射
                auto_mapping = guess_column_mapping(list(df.columns))
                
                # 让用户确认或修改映射
                col1, col2, col3 = st.columns(3)
                
                all_columns = ['(不选择)'] + list(df.columns)
                
                with col1:
                    st.markdown("**📘 规范名称**")
                    default_idx_1 = all_columns.index(auto_mapping['规范']) if auto_mapping['规范'] in all_columns else 0
                    col_spec = st.selectbox(
                        "选择对应列",
                        all_columns,
                        index=default_idx_1,
                        key="map_spec",
                        label_visibility="collapsed"
                    )
                
                with col2:
                    st.markdown("**📑 条文号**")
                    default_idx_2 = all_columns.index(auto_mapping['条文']) if auto_mapping['条文'] in all_columns else 0
                    col_clause = st.selectbox(
                        "选择对应列",
                        all_columns,
                        index=default_idx_2,
                        key="map_clause",
                        label_visibility="collapsed"
                    )
                
                with col3:
                    st.markdown("**📝 条文内容**")
                    default_idx_3 = all_columns.index(auto_mapping['条文内容']) if auto_mapping['条文内容'] in all_columns else 0
                    col_content = st.selectbox(
                        "选择对应列",
                        all_columns,
                        index=default_idx_3,
                        key="map_content",
                        label_visibility="collapsed"
                    )
                
                # 构建最终映射
                final_mapping = {
                    '规范': col_spec if col_spec != '(不选择)' else None,
                    '条文': col_clause if col_clause != '(不选择)' else None,
                    '条文内容': col_content if col_content != '(不选择)' else None
                }
                
                # 预览转换后的数据
                st.markdown("---")
                st.markdown("### 👁️ 转换预览")
                
                preview_df = apply_column_mapping(df, final_mapping)
                st.dataframe(
                    preview_df.head(10)[['规范', '条文', '条文内容']],
                    use_container_width=True,
                    hide_index=True
                )
                
                st.caption(f"预览前10行，共 {len(preview_df)} 条数据")
                
                # 导入按钮
                st.markdown("---")
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("✅ 确认导入", type="primary", use_container_width=True):
                        # 检查是否至少选择了一列
                        if not any(final_mapping.values()):
                            st.error("❌ 请至少选择一列进行映射")
                        else:
                            st.session_state.df = preview_df
                            save_current_project()
                            st.session_state.show_import_modal = False
                            st.success(f"✅ 成功导入 {len(preview_df)} 条数据！")
                            st.balloons()
                            st.rerun()
                
                with col_btn2:
                    if st.button("❌ 取消", use_container_width=True):
                        st.session_state.show_import_modal = False
                        st.rerun()
                        
            except Exception as e:
                st.error(f"❌ 文件处理失败: {str(e)}")
                st.info("💡 请确保文件格式正确，或尝试其他编码保存文件")
        
        else:
            st.markdown("---")
            st.markdown("### 📖 支持的文件格式")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                **CSV 文件**
                - 任意列名均可
                - 支持 UTF-8、GBK 等编码
                - 建议使用逗号分隔
                """)
            
            with col2:
                st.markdown("""
                **Excel 文件**
                - 支持 .xlsx 和 .xls
                - 自动读取第一个工作表
                - 第一行作为列名
                """)
            
            st.markdown("---")
            st.markdown("### 📝 示例")
            st.markdown("您的文件可以是这样的（列名任意）：")
            
            example_data = pd.DataFrame({
                "标准名": ["GB50016-2014", "GB50016-2014"],
                "章节": ["5.1.1", "5.1.2"],
                "内容描述": ["建筑高度大于27m的住宅建筑...", "建筑高度大于100m的民用建筑..."]
            })
            st.dataframe(example_data, use_container_width=True, hide_index=True)
            st.caption("系统会自动识别并映射为: 规范、条文、条文内容")
            
            if st.button("❌ 关闭", key="close_import"):
                st.session_state.show_import_modal = False
                st.rerun()

# ==================== 其他弹窗 ====================
def show_new_project_modal():
    """新建项目弹窗"""
    if not st.session_state.show_new_project_modal:
        return
    
    with st.expander("🆕 新建项目", expanded=True):
        with st.form(key="new_project_form"):
            project_name = st.text_input(
                "项目名称",
                placeholder="请输入项目名称",
                key="new_project_name_input"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("✅ 创建项目", type="primary", use_container_width=True)
            with col2:
                cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
            
            if submitted:
                if project_name.strip():
                    success, message = create_new_project(project_name.strip())
                    if success:
                        st.session_state.show_new_project_modal = False
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("❌ 项目名称不能为空！")
            
            if cancelled:
                st.session_state.show_new_project_modal = False
                st.rerun()

def show_load_project_modal():
    """加载项目弹窗"""
    if not st.session_state.show_load_project_modal:
        return
    
    with st.expander("📂 打开项目", expanded=True):
        projects = list(st.session_state.projects.keys())
        
        if projects:
            selected_project = st.selectbox("选择项目", projects, key="select_project")
            
            if selected_project:
                project_info = st.session_state.projects[selected_project]
                st.caption(f"创建时间: {project_info.get('created_at', '未知')}")
                data_count = len(project_info.get('data', []))
                st.caption(f"数据条数: {data_count}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 加载项目", type="primary", use_container_width=True):
                    if load_project(selected_project):
                        st.session_state.show_load_project_modal = False
                        st.success(f"✅ 项目 '{selected_project}' 加载成功！")
                        st.rerun()
            
            with col2:
                if st.button("❌ 取消", use_container_width=True, key="cancel_load"):
                    st.session_state.show_load_project_modal = False
                    st.rerun()
        else:
            st.info("📭 当前没有可用项目")
            if st.button("🆕 创建新项目", type="primary", use_container_width=True):
                st.session_state.show_new_project_modal = True
                st.session_state.show_load_project_modal = False
                st.rerun()
            
            if st.button("❌ 关闭", key="close_load_empty"):
                st.session_state.show_load_project_modal = False
                st.rerun()

def show_ontology_modal():
    """本体操作弹窗"""
    if not st.session_state.show_ontology_modal:
        return
    
    with st.expander("🧠 本体操作", expanded=True):
        tab1, tab2, tab3 = st.tabs(["📥 载入本体", "📊 本体概览", "🔨 编辑本体"])
        
        with tab1:
            uploaded_onto = st.file_uploader("上传本体文件 (JSON)", type="json", key="upload_ontology")
            if uploaded_onto:
                try:
                    onto_data = json.load(uploaded_onto)
                    st.json(onto_data)
                    if st.button("确认载入", type="primary"):
                        st.session_state.knowledge_graph = onto_data
                        save_current_project()
                        st.success("✅ 本体载入成功！")
                        st.rerun()
                except Exception as e:
                    st.error(f"解析失败: {e}")
        
        with tab2:
            kg = st.session_state.knowledge_graph
            col1, col2 = st.columns(2)
            with col1:
                st.metric("节点数", len(kg.get('nodes', [])))
            with col2:
                st.metric("边数", len(kg.get('edges', [])))
            
            if kg.get('nodes'):
                st.markdown("**节点列表:**")
                for node in kg['nodes'][:10]:
                    st.write(f"- {node.get('label', node.get('id', '未知'))}")
                if len(kg['nodes']) > 10:
                    st.caption(f"... 还有 {len(kg['nodes']) - 10} 个节点")
        
        with tab3:
            new_node = st.text_input("添加新节点", placeholder="输入节点名称")
            if st.button("➕ 添加节点", type="primary") and new_node:
                if 'nodes' not in st.session_state.knowledge_graph:
                    st.session_state.knowledge_graph['nodes'] = []
                st.session_state.knowledge_graph['nodes'].append({
                    'id': new_node,
                    'label': new_node
                })
                save_current_project()
                st.success(f"✅ 添加节点: {new_node}")
                st.rerun()
        
        st.markdown("---")
        if st.button("❌ 关闭", key="close_ontology"):
            st.session_state.show_ontology_modal = False
            st.rerun()

# ==================== 主页面 ====================
def show_main_page():
    """显示主页面"""
    # 顶部操作栏
    st.markdown("### 📋 条文操作")
    ac1, ac2, ac3, ac4 = st.columns(4)
    
    with ac1:
        if st.button("🗑️ 删除条文", use_container_width=True):
            st.toast("删除功能开发中", icon="🔧")
        if st.button("🔢 修改序号", use_container_width=True):
            st.toast("修改序号功能开发中", icon="🔧")
    
    with ac2:
        if st.button("➕ 插入条文", use_container_width=True):
            st.toast("插入功能开发中", icon="🔧")
        st.button("✂️ 拆解条文", use_container_width=True, disabled=True)
    
    with ac3:
        if st.button("🕸️ 图谱建模", type="primary", use_container_width=True):
            st.session_state.current_view = 'graph_modeling'
            st.rerun()
        st.button("🔄 重新建模", use_container_width=True, disabled=True)
    
    with ac4:
        st.button("🏷️ 标注规则", type="primary", use_container_width=True, disabled=True)
        st.button("📝 重写规则", use_container_width=True, disabled=True)
    
    st.markdown("---")
    
    # 数据表格
    display_df = st.session_state.df
    
    if display_df.empty:
        st.info("📭 暂无数据，请通过侧边栏 **导入规范** 添加数据")
        
        st.markdown("### 💡 快速开始")
        st.markdown("""
        1. 点击左侧 **📥 导入规范** 按钮
        2. 上传您的 CSV 或 Excel 文件（任意列名均可）
        3. 系统自动识别列，您确认映射后即可导入
        """)
        
        # 示例数据
        st.markdown("### 📝 数据格式示例")
        example_df = pd.DataFrame({
            "规范": ["GB50016-2014", "GB50016-2014"],
            "条文": ["5.1.1", "5.1.2"],
            "条文内容": ["建筑高度大于27m的住宅建筑...", "建筑高度大于100m的民用建筑..."],
            "实体标注": [False, False],
            "关系标注": [False, False],
            "规则标注": [False, False]
        })
        st.dataframe(example_df, use_container_width=True, hide_index=True)
    else:
        column_config = {
            "规范": st.column_config.TextColumn("规范", width="medium"),
            "条文": st.column_config.TextColumn("条文号", width="small"),
            "条文内容": st.column_config.TextColumn("条文内容", width="large"),
            "实体标注": st.column_config.CheckboxColumn("实体", width="small"),
            "关系标注": st.column_config.CheckboxColumn("关系", width="small"),
            "规则标注": st.column_config.CheckboxColumn("规则", width="small"),
        }
        
        edited_df = st.data_editor(
            display_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            height=500,
            key='main_data_editor'
        )
        
        st.session_state.df = edited_df
        save_current_project()
    
    # 底部状态栏
    st.markdown("---")
    status_text = f"📊 共 {len(display_df)} 条数据"
    if st.session_state.current_project:
        status_text = f"📂 **{st.session_state.current_project}** | " + status_text + " | ✅ 就绪"
    else:
        status_text += " | ⚠️ 未选择项目"
    st.caption(status_text)

def show_graph_modeling():
    """显示图谱建模页面"""
    st.markdown("### 🕸️ 知识图谱建模")
    
    if st.button("⬅️ 返回主页", type="secondary"):
        st.session_state.current_view = 'main'
        st.rerun()
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### 📊 本体信息")
        kg = st.session_state.knowledge_graph
        st.metric("节点数", len(kg.get('nodes', [])))
        st.metric("边数", len(kg.get('edges', [])))
        
        st.markdown("#### ➕ 添加节点")
        new_node = st.text_input("节点名称", key="graph_new_node")
        if st.button("添加", type="primary") and new_node:
            if 'nodes' not in st.session_state.knowledge_graph:
                st.session_state.knowledge_graph['nodes'] = []
            st.session_state.knowledge_graph['nodes'].append({'id': new_node, 'label': new_node})
            save_current_project()
            st.success(f"✅ 添加节点: {new_node}")
            st.rerun()
    
    with col2:
        st.markdown("#### 🗺️ 图谱可视化")
        if kg.get('nodes'):
            st.json(kg)
        else:
            st.info("📭 暂无节点数据")

# ==================== 知识图谱相关函数 ====================
def extract_entities(text: str) -> List[str]:
    """
    从文本中提取实体
    
    Args:
        text: 输入文本
        
    Returns:
        List[str]: 提取的实体列表
    """
    entities = []
    patterns = [
        r'([甲乙丙丁戊][类])',  # 类别
        r'(\d+[米])',  # 距离
        r'(\d+层)',  # 层数
        r'([一二三四][级])',  # 等级
        r'(\d+平方米)',  # 面积
        r'(防火墙|防火门|防火窗|防火卷帘)',  # 防火设施
        r'(厂房|仓库|住宅|办公楼)',  # 建筑类型
        r'(安全出口|疏散楼梯|疏散走道)',  # 安全设施
        r'(耐火极限)',  # 性能指标
        r'(\d+\.?\d*h)',  # 时间
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        entities.extend([m for m in matches if m not in entities])
    
    return entities[:10]  # 限制数量

def extract_relations(entities: List[str], text: str) -> List[Dict]:
    """
    从实体和文本中提取关系
    
    Args:
        entities: 实体列表
        text: 原文本
        
    Returns:
        List[Dict]: 关系列表
    """
    relations = []
    
    # 定义关系关键词
    relation_keywords = {
        '应采用': '要求',
        '不应低于': '标准',
        '宜': '建议',
        '应设置': '配置',
        '不应': '禁止'
    }
    
    for i, entity1 in enumerate(entities):
        for j, entity2 in enumerate(entities[i+1:], i+1):
            # 检查两个实体是否在文本中相邻或通过关系词连接
            for keyword, rel_type in relation_keywords.items():
                if keyword in text:
                    pos1 = text.find(entity1)
                    pos2 = text.find(entity2)
                    pos_key = text.find(keyword)
                    
                    if pos1 != -1 and pos2 != -1 and pos_key != -1:
                        if abs(pos1 - pos2) < 50:  # 实体距离限制
                            relations.append({
                                'source': entity1,
                                'target': entity2,
                                'relation': rel_type,
                                'description': f"{entity1} {rel_type} {entity2}"
                            })
                            break
    
    return relations[:15]  # 限制关系数量

def build_knowledge_graph() -> Dict:
    """构建知识图谱"""
    nodes = []
    edges = []
    rules = []
    
    df = st.session_state.df
    labeled_df = df[df["实体标注"] == "√"].head(50)  # 限制处理数量
    
    node_map = {}  # 用于快速查找节点ID
    
    with st.spinner("🔄 正在构建知识图谱..."):
        progress_bar = st.progress(0)
        total_rows = len(labeled_df)
        
        for idx, (index, row) in enumerate(labeled_df.iterrows()):
            # 更新进度
            progress_bar.progress((idx + 1) / total_rows)
            
            # 提取实体
            entities = extract_entities(row['条文内容'])
            
            # 创建节点
            for entity in entities:
                if entity not in node_map:
                    node_id = len(nodes) + 1
                    nodes.append({
                        'id': node_id,
                        'label': entity,
                        'type': 'entity',
                        'properties': {
                            'source': row['条文'],
                            'content': row['条文内容'][:100]
                        }
                    })
                    node_map[entity] = node_id
            
            # 提取关系
            relations = extract_relations(entities, row['条文内容'])
            
            # 创建边
            for rel in relations:
                source_id = node_map.get(rel['source'])
                target_id = node_map.get(rel['target'])
                
                if source_id and target_id and source_id != target_id:
                    edge = {
                        'id': len(edges) + 1,
                        'source': source_id,
                        'target': target_id,
                        'label': rel['relation'],
                        'description': rel['description']
                    }
                    edges.append(edge)
            
            # 构建规则
            rules.append({
                'id': len(rules) + 1,
                'content': row['条文内容'][:200] + "..." if len(row['条文内容']) > 200 else row['条文内容'],
                'source': row['条文'],
                'entities': entities
            })
        
        progress_bar.empty()
    
    return {
        'nodes': nodes,
        'edges': edges,
        'rules': rules
    }

# ==================== UI组件 ====================
def render_modal_header(title: str):
    """渲染弹窗头部"""
    st.markdown(f"""
    <div class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>{title}</h3>
            </div>
    """, unsafe_allow_html=True)

def render_modal_footer():
    """渲染弹窗尾部"""
    st.markdown("</div></div></div>", unsafe_allow_html=True)

def render_stat_box(label: str, value: int) -> str:
    """渲染统计框"""
    return f"""
    <div class="metric-box">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """

# ==================== 侧边栏 ====================
def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("📂 项目管理")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🆕 新建", type="primary", use_container_width=True):
                st.session_state.show_new_project_modal = True
                st.rerun()
        with col2:
            if st.button("📂 打开", use_container_width=True):
                st.session_state.show_load_project_modal = True
                st.rerun()
        
        if st.session_state.current_project:
            st.success(f"**当前:** {st.session_state.current_project}")
            if st.button("💾 导出项目", use_container_width=True):
                export_project()
        else:
            st.warning("⚠️ 未选择项目")
        
        st.markdown("---")
        st.header("📄 文件操作")
        
        if st.button("📥 导入规范", type="primary", use_container_width=True):
            st.session_state.show_import_modal = True
            st.rerun()
        
        if st.button("🧠 本体操作", use_container_width=True):
            st.session_state.show_ontology_modal = True
            st.rerun()
        
        st.markdown("---")
        st.header("📈 统计")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("数据", len(st.session_state.df))
        with col2:
            st.metric("项目", len(st.session_state.projects))
        
        # 标注进度
        if not st.session_state.df.empty:
            total = len(st.session_state.df)
            entity_done = st.session_state.df['实体标注'].sum() if '实体标注' in st.session_state.df.columns else 0
            relation_done = st.session_state.df['关系标注'].sum() if '关系标注' in st.session_state.df.columns else 0
            rule_done = st.session_state.df['规则标注'].sum() if '规则标注' in st.session_state.df.columns else 0
            
            st.markdown("---")
            st.markdown("**📊 标注进度**")
            
            # 实体标注进度
            entity_pct = int(entity_done / total * 100) if total > 0 else 0
            st.progress(entity_pct / 100, text=f"实体: {entity_pct}%")
            
            # 关系标注进度
            relation_pct = int(relation_done / total * 100) if total > 0 else 0
            st.progress(relation_pct / 100, text=f"关系: {relation_pct}%")
            
            # 规则标注进度
            rule_pct = int(rule_done / total * 100) if total > 0 else 0
            st.progress(rule_pct / 100, text=f"规则: {rule_pct}%")

# ==================== 快速导入功能（从本地路径） ====================
def quick_import_from_path():
    """从本地路径快速导入（用于测试）"""
    with st.expander("🔧 开发者工具：从本地路径导入", expanded=False):
        local_path = st.text_input(
            "输入本地文件路径",
            placeholder=r"例如: E:\data\规范.csv",
            key="local_path_input"
        )
        
        if st.button("📂 从路径导入", key="import_from_path"):
            if local_path and Path(local_path).exists():
                try:
                    file_path = Path(local_path)
                    
                    # 根据扩展名读取
                    if file_path.suffix.lower() == '.csv':
                        # 尝试多种编码
                        for encoding in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
                            try:
                                df = pd.read_csv(file_path, encoding=encoding)
                                break
                            except:
                                continue
                    elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                        df = pd.read_excel(file_path)
                    else:
                        st.error("不支持的文件格式")
                        return
                    
                    # 自动映射列
                    mapping = guess_column_mapping(list(df.columns))
                    result_df = apply_column_mapping(df, mapping)
                    
                    st.session_state.df = result_df
                    save_current_project()
                    st.success(f"✅ 成功导入 {len(result_df)} 条数据！")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"导入失败: {str(e)}")
            else:
                st.warning("请输入有效的文件路径")

# ==================== 批量操作功能 ====================
def show_batch_operations():
    """显示批量操作选项"""
    if st.session_state.df.empty:
        return
    
    with st.expander("🔧 批量操作", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ 全部标记实体", use_container_width=True):
                st.session_state.df['实体标注'] = True
                save_current_project()
                st.success("已标记全部实体")
                st.rerun()
        
        with col2:
            if st.button("✅ 全部标记关系", use_container_width=True):
                st.session_state.df['关系标注'] = True
                save_current_project()
                st.success("已标记全部关系")
                st.rerun()
        
        with col3:
            if st.button("✅ 全部标记规则", use_container_width=True):
                st.session_state.df['规则标注'] = True
                save_current_project()
                st.success("已标记全部规则")
                st.rerun()
        
        st.markdown("---")
        
        col4, col5, col6 = st.columns(3)
        
        with col4:
            if st.button("❌ 清除实体标注", use_container_width=True):
                st.session_state.df['实体标注'] = False
                save_current_project()
                st.success("已清除实体标注")
                st.rerun()
        
        with col5:
            if st.button("❌ 清除关系标注", use_container_width=True):
                st.session_state.df['关系标注'] = False
                save_current_project()
                st.success("已清除关系标注")
                st.rerun()
        
        with col6:
            if st.button("❌ 清除规则标注", use_container_width=True):
                st.session_state.df['规则标注'] = False
                save_current_project()
                st.success("已清除规则标注")
                st.rerun()
        
        st.markdown("---")
        
        # 数据导出
        st.markdown("**📤 导出数据**")
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            csv_data = st.session_state.df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📄 导出CSV",
                data=csv_data,
                file_name=f"规范数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_exp2:
            json_data = st.session_state.df.to_json(orient='records', force_ascii=False, indent=2)
            st.download_button(
                label="📋 导出JSON",
                data=json_data,
                file_name=f"规范数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

# ==================== 搜索和筛选功能 ====================
def show_search_filter():
    """显示搜索和筛选功能"""
    if st.session_state.df.empty:
        return
    
    with st.expander("🔍 搜索与筛选", expanded=False):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            search_text = st.text_input(
                "搜索内容",
                placeholder="输入关键词搜索条文内容...",
                key="search_input"
            )
        
        with col2:
            filter_option = st.selectbox(
                "筛选条件",
                ["全部", "已标注实体", "未标注实体", "已标注关系", "未标注关系", "已标注规则", "未标注规则"],
                key="filter_select"
            )
        
        # 应用搜索和筛选
        filtered_df = st.session_state.df.copy()
        
        if search_text:
            mask = filtered_df['条文内容'].str.contains(search_text, case=False, na=False)
            mask |= filtered_df['规范'].str.contains(search_text, case=False, na=False)
            mask |= filtered_df['条文'].str.contains(search_text, case=False, na=False)
            filtered_df = filtered_df[mask]
        
        if filter_option == "已标注实体":
            filtered_df = filtered_df[filtered_df['实体标注'] == True]
        elif filter_option == "未标注实体":
            filtered_df = filtered_df[filtered_df['实体标注'] == False]
        elif filter_option == "已标注关系":
            filtered_df = filtered_df[filtered_df['关系标注'] == True]
        elif filter_option == "未标注关系":
            filtered_df = filtered_df[filtered_df['关系标注'] == False]
        elif filter_option == "已标注规则":
            filtered_df = filtered_df[filtered_df['规则标注'] == True]
        elif filter_option == "未标注规则":
            filtered_df = filtered_df[filtered_df['规则标注'] == False]
        
        if search_text or filter_option != "全部":
            st.info(f"🔍 找到 {len(filtered_df)} 条匹配记录")
            
            if not filtered_df.empty:
                st.dataframe(
                    filtered_df[['规范', '条文', '条文内容']],
                    use_container_width=True,
                    hide_index=True,
                    height=300
                )

# ==================== 增强的主页面 ====================
def show_main_page_enhanced():
    """显示增强版主页面"""
    # 顶部操作栏
    st.markdown("### 📋 条文操作")
    ac1, ac2, ac3, ac4 = st.columns(4)
    
    with ac1:
        if st.button("🗑️ 删除条文", use_container_width=True):
            st.toast("删除功能开发中", icon="🔧")
        if st.button("🔢 修改序号", use_container_width=True):
            st.toast("修改序号功能开发中", icon="🔧")
    
    with ac2:
        if st.button("➕ 插入条文", use_container_width=True):
            st.toast("插入功能开发中", icon="🔧")
        st.button("✂️ 拆解条文", use_container_width=True, disabled=True)
    
    with ac3:
        if st.button("🕸️ 图谱建模", type="primary", use_container_width=True):
            st.session_state.current_view = 'graph_modeling'
            st.rerun()
        st.button("🔄 重新建模", use_container_width=True, disabled=True)
    
    with ac4:
        st.button("🏷️ 标注规则", type="primary", use_container_width=True, disabled=True)
        st.button("📝 重写规则", use_container_width=True, disabled=True)
    
    # 搜索筛选
    show_search_filter()
    
    # 批量操作
    show_batch_operations()
    
    st.markdown("---")
    
    # 数据表格
    display_df = st.session_state.df
    
    if display_df.empty:
        st.info("📭 暂无数据，请通过侧边栏 **导入规范** 添加数据")
        
        st.markdown("### 💡 快速开始")
        st.markdown("""
        1. 点击左侧 **📥 导入规范** 按钮
        2. 上传您的 CSV 或 Excel 文件（**任意列名均可**）
        3. 系统自动识别列，您确认映射后即可导入
        """)
        
        # 支持的格式说明
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **✅ 支持的文件格式**
            - CSV 文件 (.csv)
            - Excel 文件 (.xlsx, .xls)
            """)
        with col2:
            st.markdown("""
            **✅ 自动识别的列名**
            - 规范/标准/规范名称
            - 条文/章节/条文号
            - 内容/条文内容/描述
            """)
        
        # 示例数据
        st.markdown("### 📝 数据格式示例")
        example_df = pd.DataFrame({
            "规范": ["GB50016-2014", "GB50016-2014", "GB50016-2014"],
            "条文": ["5.1.1", "5.1.2", "5.1.3"],
            "条文内容": [
                "建筑高度大于27m的住宅建筑应设置消防电梯...",
                "建筑高度大于100m的民用建筑应设置避难层...",
                "高层建筑的疏散楼梯应采用防烟楼梯间..."
            ],
            "实体标注": [False, False, False],
            "关系标注": [False, False, False],
            "规则标注": [False, False, False]
        })
        st.dataframe(example_df, use_container_width=True, hide_index=True)
        
        # 开发者工具
        quick_import_from_path()
        
    else:
        column_config = {
            "规范": st.column_config.TextColumn("规范", width="medium"),
            "条文": st.column_config.TextColumn("条文号", width="small"),
            "条文内容": st.column_config.TextColumn("条文内容", width="large"),
            "实体标注": st.column_config.CheckboxColumn("实体", width="small"),
            "关系标注": st.column_config.CheckboxColumn("关系", width="small"),
            "规则标注": st.column_config.CheckboxColumn("规则", width="small"),
        }
        
        edited_df = st.data_editor(
            display_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            height=500,
            num_rows="dynamic",  # 允许添加/删除行
            key='main_data_editor'
        )
        
        # 检测变化并保存
        if not edited_df.equals(st.session_state.df):
            st.session_state.df = edited_df
            save_current_project()
    
    # 底部状态栏
    st.markdown("---")
    status_cols = st.columns([2, 1, 1, 1])
    
    with status_cols[0]:
        if st.session_state.current_project:
            st.caption(f"📂 **{st.session_state.current_project}**")
        else:
            st.caption("⚠️ 未选择项目")
    
    with status_cols[1]:
        st.caption(f"📊 {len(display_df)} 条数据")
    
    with status_cols[2]:
        if not display_df.empty:
            done = display_df['实体标注'].sum() + display_df['关系标注'].sum() + display_df['规则标注'].sum()
            total = len(display_df) * 3
            pct = int(done / total * 100) if total > 0 else 0
            st.caption(f"📈 完成度: {pct}%")
    
    with status_cols[3]:
        st.caption("✅ 就绪")

# ==================== 主程序入口 ====================
def main():
    """主程序入口"""
    # 初始化
    init_session_state()
    load_custom_css()
    
    # 渲染侧边栏
    render_sidebar()
    
    # 显示弹窗
    show_import_modal()
    show_new_project_modal()
    show_load_project_modal()
    show_ontology_modal()
    
    # 页面标题
    st.title("🏗️ 建筑设计规范 - 知识图谱标注工具")
    
    # 页面路由
    if st.session_state.current_view == 'graph_modeling':
        show_graph_modeling()
    else:
        show_main_page_enhanced()

# 运行主程序
if __name__ == "__main__":
    main()