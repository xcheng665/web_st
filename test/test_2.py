import streamlit as st
import pandas as pd
import os
import networkx as nx
from pyvis.network import Network
import json
import re
from typing import Dict, List, Tuple
import csv
from io import StringIO
from pathlib import Path
import zipfile
from datetime import datetime

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="建筑设计规范 - 知识图谱标注工具",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自定义样式 ====================
def load_custom_css():
    """加载自定义CSS样式"""
    st.markdown("""
        <style>
            .block-container {
                padding-top: 1rem;
                padding-bottom: 1rem;
            }
            .stDataFrame {
                font-size: 14px;
            }
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
            .graph-container {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .control-panel {
                background-color: #f9f9f9;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
            }
            .rule-container {
                background-color: #fff3e0;
                border-left: 4px solid #ff9800;
                padding: 15px;
                margin: 10px 0;
                border-radius: 4px;
            }
            .modal {
                display: block;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.4);
                animation: fadeIn 0.3s;
            }
            @keyframes fadeIn {
                from {opacity: 0;}
                to {opacity: 1;}
            }
            .modal-content {
                background-color: #fefefe;
                margin: 5% auto;
                padding: 20px;
                border: 1px solid #888;
                border-radius: 8px;
                width: 80%;
                max-width: 700px;
                max-height: 85vh;
                overflow-y: auto;
                animation: slideDown 0.3s;
            }
            @keyframes slideDown {
                from {transform: translateY(-50px); opacity: 0;}
                to {transform: translateY(0); opacity: 1;}
            }
            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                border-bottom: 2px solid #e0e0e0;
                padding-bottom: 10px;
            }
            .modal-buttons {
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                margin-top: 20px;
            }
            .project-card {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0;
            }
            .project-card:hover {
                background-color: #e9ecef;
                cursor: pointer;
            }
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

# ==================== 项目管理 ====================
def init_projects():
    """初始化项目管理会话状态"""
    if 'projects' not in st.session_state:
        st.session_state['projects'] = {}
    if 'current_project' not in st.session_state:
        st.session_state['current_project'] = None
    if 'current_project_path' not in st.session_state:
        st.session_state['current_project_path'] = None

init_projects()

def create_new_project(project_name):
    """创建新项目"""
    if project_name in st.session_state.projects:
        return False, f"项目 '{project_name}' 已存在"
    
    # 创建项目目录
    project_dir = Path("projects") / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化项目文件
    clauses_file = project_dir / "clauses.csv"
    ontology_file = project_dir / "ontology.json"
    annotations_file = project_dir / "annotations.json"
    
    # 创建空的CSV文件
    empty_df = pd.DataFrame(columns=['id', '规范', '条文', '条文内容', '实体标注', '关系标注', '规则标注'])
    empty_df.to_csv(clauses_file, index=False, encoding='utf-8')
    
    # 创建空的本体文件
    empty_ontology = {
        "entities": [],
        "relations": [],
        "attributes": []
    }
    with open(ontology_file, 'w', encoding='utf-8') as f:
        json.dump(empty_ontology, f, ensure_ascii=False, indent=2)
    
    # 创建空的标注文件
    empty_annotations = []
    with open(annotations_file, 'w', encoding='utf-8') as f:
        json.dump(empty_annotations, f, ensure_ascii=False, indent=2)
    
    st.session_state.projects[project_name] = {
        'path': str(project_dir),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'clauses_file': str(clauses_file),
        'ontology_file': str(ontology_file),
        'annotations_file': str(annotations_file)
    }
    
    st.session_state.current_project = project_name
    st.session_state.current_project_path = str(project_dir)
    return True, f"项目 '{project_name}' 创建成功"

def load_project(project_name):
    """加载项目"""
    if project_name in st.session_state.projects:
        project_info = st.session_state.projects[project_name]
        project_dir = Path(project_info['path'])
        
        # 加载条文数据
        clauses_file = project_dir / "clauses.csv"
        if clauses_file.exists():
            df = pd.read_csv(clauses_file, encoding='utf-8')
            st.session_state.df = df
        else:
            st.session_state.df = pd.DataFrame(columns=['id', '规范', '条文', '条文内容', '实体标注', '关系标注', '规则标注'])
        
        # 加载本体数据
        ontology_file = project_dir / "ontology.json"
        if ontology_file.exists():
            with open(ontology_file, 'r', encoding='utf-8') as f:
                st.session_state.knowledge_graph = json.load(f)
        else:
            st.session_state.knowledge_graph = {'nodes': [], 'edges': [], 'rules': []}
        
        st.session_state.current_project = project_name
        st.session_state.current_project_path = str(project_dir)
        return True
    return False

def export_project():
    """导出当前项目"""
    if not st.session_state.current_project:
        st.warning("请先选择一个项目")
        return
    
    project_dir = Path(st.session_state.current_project_path)
    zip_path = f"{st.session_state.current_project}_export.zip"
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_path in project_dir.glob("*"):
            zipf.write(file_path, file_path.name)
    
    with open(zip_path, "rb") as f:
        st.download_button(
            label="📥 下载项目文件",
            data=f,
            file_name=zip_path,
            mime="application/zip"
        )

# ==================== 会话状态初始化 ====================
def init_session_state():
    """初始化会话状态变量"""
    defaults = {
        'current_view': 'main',
        'knowledge_graph': {'nodes': [], 'edges': [], 'rules': []},
        'selected_row': None,
        'show_delete_modal': False,
        'show_insert_modal': False,
        'show_edit_modal': False,
        'editing_row': None,
        'delete_id': 1,
        'edit_id': 1,
        'last_spec': "GB50016-2014(2018年版)",
        'df': None,
        'show_import_modal': False,
        'show_new_project_modal': False,
        'show_load_project_modal': False,
        'show_ontology_modal': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()
file_path = r"E:\Users\czy\Desktop\标注工具V4.0项目\标注工具V4.0\设计规范集\GB 50016-2014(2018年版) 建筑设计防火规范.csv"
# ==================== 数据加载与处理 ====================
def import_from_csv(file):
    """从CSV文件导入数据"""
        
    string_data = StringIO(file.getvalue().decode("utf-8"))
    df = pd.read_csv(string_data)
        
        # 检查必需列是否存在
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
        
        df['id'] = range(1, len(df) + 1)
        df['实体标注'] = ''
        df['关系标注'] = ''
        df['规则标注'] = ''
        st.session_state.df = df[['id', '规范', '条文', '条文内容', '实体标注', '关系标注', '规则标注']]
            
            # 保存到当前项目
        if st.session_state.current_project_path:
                project_dir = Path(st.session_state.current_project_path)
                clauses_file = project_dir / "clauses.csv"
                st.session_state.df.to_csv(clauses_file, index=False, encoding='utf-8')
            
            

def import_from_json(file):
    """从JSON文件导入数据"""
    try:
        data = json.load(file)
        
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict) and '条文列表' in data:
            df = pd.DataFrame(data['条文列表'])
        else:
            st.error("JSON格式不符合预期")
            return False
        
        # 检查必需列是否存在
        required_columns = ['规范', '条文', '条文内容']
        if all(col in df.columns for col in required_columns):
            df['id'] = range(1, len(df) + 1)
            df['实体标注'] = ''
            df['关系标注'] = ''
            df['规则标注'] = ''
            st.session_state.df = df[['id', '规范', '条文', '条文内容', '实体标注', '关系标注', '规则标注']]
            
            # 保存到当前项目
            if st.session_state.current_project_path:
                project_dir = Path(st.session_state.current_project_path)
                clauses_file = project_dir / "clauses.csv"
                st.session_state.df.to_csv(clauses_file, index=False, encoding='utf-8')
            
            return True
        else:
            st.error("JSON数据缺少必需字段: '规范', '条文', '条文内容'")
            return False
    except Exception as e:
        st.error(f"导入JSON文件时出错: {str(e)}")
        return False

def import_ontology(file):
    """导入本体文件"""
    try:
        content = file.getvalue().decode("utf-8")
        
        # 解析本体内容
        try:
            ontology_data = json.loads(content)
        except json.JSONDecodeError:
            # 如果不是JSON格式，创建默认结构
            ontology_data = {
                "entities": [],
                "relations": [],
                "attributes": []
            }
            st.info(f"文件 {file.name} 不是有效的JSON格式，已创建空本体结构")
        
        st.session_state.knowledge_graph = ontology_data
        
        # 保存到当前项目
        if st.session_state.current_project_path:
            project_dir = Path(st.session_state.current_project_path)
            ontology_file = project_dir / "ontology.json"
            with open(ontology_file, 'w', encoding='utf-8') as f:
                json.dump(ontology_data, f, ensure_ascii=False, indent=2)
        
        st.success(f"✅ 成功从本体文件 {file.name} 导入数据！")
        return True
    except Exception as e:
        st.error(f"导入本体文件时出错: {str(e)}")
        return False

def show_import_modal():
    """导入规范弹窗"""
    if not st.session_state.get('show_import_modal', False):
        return
    
    with st.container():
        st.markdown("**选择导入方式:**")
        
        import_option = st.radio(
            "导入类型",
            ("CSV文件", "JSON文件", "本体文件"),
            key="import_type"
        )
        
        uploaded_file = st.file_uploader(
            f"上传{import_option}文件",
            type=['csv', 'json', 'rdf', 'ttl', 'n3', 'owl'] if import_option == "本体文件" else ['csv'] if import_option == "CSV文件" else ['json'],
            key=f"upload_{import_option}"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("导入", type="primary", use_container_width=True, key="import_confirm"):
                if uploaded_file is not None:
                    success = False
                    if import_option == "CSV文件":
                        success = import_from_csv(uploaded_file)
                    elif import_option == "JSON文件":
                        success = import_from_json(uploaded_file)
                    elif import_option == "本体文件":
                        success = import_ontology(uploaded_file)
                    
                    if success:
                        st.session_state.show_import_modal = False
                        st.rerun()
                else:
                    st.warning("请先选择要上传的文件")
        
        with col2:
            if st.button("取消", type="secondary", use_container_width=True, key="import_cancel"):
                st.session_state.show_import_modal = False
                st.rerun()
        
        st.markdown("---")
        st.markdown("**格式说明:**")
        if import_option == "CSV文件":
            st.info("CSV文件应包含列: 规范, 条文, 条文内容")
        elif import_option == "JSON文件":
            st.info("JSON文件应包含数组或对象，其中包含规范、条文、条文内容字段")
        elif import_option == "本体文件":
            st.info("支持JSON、RDF/XML, Turtle(.ttl), N3, OWL等本体格式")
        
        render_modal_footer()

def show_new_project_modal():
    """新建项目弹窗"""
    if not st.session_state.show_new_project_modal:
        return
    
    with st.container():
        
        with st.form(key="new_project_form"):
            project_name = st.text_input(
                "项目名称", 
                placeholder="请输入项目名称",
                key="new_project_name_input"
            )
            
            submitted = st.form_submit_button("创建项目", type="primary")
            
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
        
        if st.button("取消", type="secondary", use_container_width=True, key="cancel_new_project"):
            st.session_state.show_new_project_modal = False
            st.rerun()
        
        render_modal_footer()

def show_load_project_modal():
    """加载项目弹窗"""
    if not st.session_state.show_load_project_modal:
        return
    
    with st.container():      
        projects = list(st.session_state.projects.keys())
        if projects:
            selected_project = st.selectbox("选择项目", projects)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("加载项目", type="primary", use_container_width=True):
                    if load_project(selected_project):
                        st.session_state.show_load_project_modal = False
                        st.success(f"✅ 项目 '{selected_project}' 加载成功！")
                        st.rerun()
                    else:
                        st.error("加载项目失败")
            
            with col2:
                if st.button("取消", type="secondary", use_container_width=True):
                    st.session_state.show_load_project_modal = False
                    st.rerun()
        else:
            st.info("当前没有可用项目")
            if st.button("创建新项目", type="primary", use_container_width=True):
                st.session_state.show_new_project_modal = True
                st.session_state.show_load_project_modal = False
                st.rerun()
        
        render_modal_footer()

def show_ontology_modal():
    """本体操作弹窗"""
    if not st.session_state.show_ontology_modal:
        return
    
    with st.container():      
        tab1, tab2, tab3 = st.tabs(["载入本体", "更新本体", "构建本体"])
        
        with tab1:
            uploaded_onto = st.file_uploader("上传 ontology.json", type="json", key="upload_ontology")
            if uploaded_onto is not None:
                try:
                    new_onto = json.load(uploaded_onto)
                    st.session_state.knowledge_graph = new_onto
                    
                    # 保存到当前项目
                    if st.session_state.current_project_path:
                        project_dir = Path(st.session_state.current_project_path)
                        ontology_file = project_dir / "ontology.json"
                        with open(ontology_file, 'w', encoding='utf-8') as f:
                            json.dump(new_onto, f, ensure_ascii=False, indent=2)
                    
                    st.success("✅ 本体载入成功！")
                except Exception as e:
                    st.error(f"❌ 无效 JSON：{e}")
        
        with tab2:
            onto_str = st.text_area(
                "本体内容（JSON 格式）", 
                value=json.dumps(st.session_state.knowledge_graph, ensure_ascii=False, indent=2), 
                height=300
            )
            if st.button("保存本体", type="primary", use_container_width=True):
                try:
                    updated_onto = json.loads(onto_str)
                    st.session_state.knowledge_graph = updated_onto
                    
                    # 保存到当前项目
                    if st.session_state.current_project_path:
                        project_dir = Path(st.session_state.current_project_path)
                        ontology_file = project_dir / "ontology.json"
                        with open(ontology_file, 'w', encoding='utf-8') as f:
                            json.dump(updated_onto, f, ensure_ascii=False, indent=2)
                    
                    st.success("✅ 本体已更新！")
                except json.JSONDecodeError:
                    st.error("❌ JSON 格式错误")
        
        with tab3:
            new_entity = st.text_input("新增实体类型（如：材料、构件、荷载）", key="new_entity_input")
            if st.button("添加实体", type="primary", use_container_width=True) and new_entity.strip():
                if 'entities' not in st.session_state.knowledge_graph:
                    st.session_state.knowledge_graph['entities'] = []
                
                if new_entity not in st.session_state.knowledge_graph["entities"]:
                    st.session_state.knowledge_graph["entities"].append(new_entity)
                    
                    # 保存到当前项目
                    if st.session_state.current_project_path:
                        project_dir = Path(st.session_state.current_project_path)
                        ontology_file = project_dir / "ontology.json"
                        with open(ontology_file, 'w', encoding='utf-8') as f:
                            json.dump(st.session_state.knowledge_graph, f, ensure_ascii=False, indent=2)
                    
                    st.success(f"✅ 实体 '{new_entity}' 已添加")
                else:
                    st.warning("⚠️ 实体已存在")
        
        st.markdown("### 📖 当前本体预览")
        st.json(st.session_state.knowledge_graph)
        
        if st.button("关闭", type="secondary", use_container_width=True):
            st.session_state.show_ontology_modal = False
            st.rerun()
        
        render_modal_footer()

@st.cache_data
def load_data_from_file(file_path: str) -> pd.DataFrame:
    """
    从CSV文件加载防火规范数据
    
    Args:
        file_path: CSV文件路径
        
    Returns:
        DataFrame: 加载的数据
    """
    df = pd.DataFrame(columns=["规范名称", "条文号", "条文内容"])
    
    if not os.path.exists(file_path):
        st.error(f"❌ 未找到文件: {file_path}")
        return pd.DataFrame(columns=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
    
    try:
        # 尝试UTF-8编码
        df = pd.read_csv(file_path, header=None, names=["规范名称", "条文号", "条文内容"], encoding='utf-8')
    except UnicodeDecodeError:
        try:
            # 尝试GBK编码
            df = pd.read_csv(file_path, header=None, names=["规范名称", "条文号", "条文内容"], encoding='gbk')
        except Exception as e:
            st.error(f"❌ CSV编码错误: {e}")
            return pd.DataFrame(columns=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
    except Exception as e:
        st.error(f"❌ 读取文件出错: {e}")
        return pd.DataFrame(columns=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
    
    if df.empty:
        st.warning("⚠️ 文件内容为空")
        return pd.DataFrame(columns=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
    
    return df

def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    准备DataFrame,添加必要的列
    
    Args:
        df: 原始DataFrame
        
    Returns:
        DataFrame: 处理后的DataFrame
    """
    df["id"] = range(1, len(df) + 1)
    df["实体标注"] = ""
    df["关系标注"] = ""
    df["规则标注"] = ""
    
    # 模拟标注状态(实际应从数据库读取)
    for index in df.index:
        if index % 3 == 0:
            df.at[index, "实体标注"] = "√"
            df.at[index, "关系标注"] = "√"
        if index % 5 == 0:
            df.at[index, "规则标注"] = "√"
    
    df.rename(columns={"规范名称": "规范", "条文号": "条文"}, inplace=True)
    
    cols = ["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"]
    return df[cols]

def get_dataframe() -> pd.DataFrame:
    """获取当前DataFrame"""
    if st.session_state.df is None:
        # 如果没有当前项目，创建一个默认项目
        if not st.session_state.current_project:
            create_new_project("默认项目")
        
        file_path = r"E:\Users\czy\Desktop\web_st\规范数据集\GB 50368-2005 住宅建筑规范.csv"
        df = load_data_from_file(file_path)
        st.session_state.df = prepare_dataframe(df) if not df.empty else df
    return st.session_state.df

# ==================== CRUD操作 ====================
def delete_row(row_id: int):
    """删除指定行"""
    df = st.session_state.df
    st.session_state.df = df[df['id'] != row_id].reset_index(drop=True)
    st.session_state.df['id'] = range(1, len(st.session_state.df) + 1)
    
    # 保存到当前项目
    if st.session_state.current_project_path:
        project_dir = Path(st.session_state.current_project_path)
        clauses_file = project_dir / "clauses.csv"
        st.session_state.df.to_csv(clauses_file, index=False, encoding='utf-8')

def insert_row(new_row_data: Dict[str, str]):
    """插入新行"""
    df = st.session_state.df
    new_row = pd.DataFrame({
        'id': [len(df) + 1],
        '规范': [new_row_data['规范']],
        '条文': [new_row_data['条文']],
        '条文内容': [new_row_data['条文内容']],
        '实体标注': [''],
        '关系标注': [''],
        '规则标注': ['']
    })
    st.session_state.df = pd.concat([df, new_row], ignore_index=True)
    
    # 保存到当前项目
    if st.session_state.current_project_path:
        project_dir = Path(st.session_state.current_project_path)
        clauses_file = project_dir / "clauses.csv"
        st.session_state.df.to_csv(clauses_file, index=False, encoding='utf-8')

def update_row(row_id: int, updated_data: Dict[str, str]):
    """更新指定行"""
    df = st.session_state.df
    mask = df['id'] == row_id
    if mask.any():
        idx = df[mask].index[0]
        df.at[idx, '规范'] = updated_data['规范']
        df.at[idx, '条文'] = updated_data['条文']
        df.at[idx, '条文内容'] = updated_data['条文内容']
    
    # 保存到当前项目
    if st.session_state.current_project_path:
        project_dir = Path(st.session_state.current_project_path)
        clauses_file = project_dir / "clauses.csv"
        st.session_state.df.to_csv(clauses_file, index=False, encoding='utf-8')

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

# ==================== 弹窗组件 ====================
def show_delete_modal():
    """删除条文弹窗"""
    if not st.session_state.show_delete_modal:
        return
    
    df = st.session_state.df
    
    if df.empty:
        st.warning("⚠️ 当前没有可删除的条文")
        if st.button("关闭", key="close_empty_delete"):
            st.session_state.show_delete_modal = False
            st.rerun()
    else:
        st.markdown("**请选择要删除的条文ID:**")
        
        st.session_state.delete_id = st.slider(
            "拖动选择条文ID",
            min_value=1,
            max_value=len(df),
            value=min(st.session_state.delete_id, len(df)),
            key="delete_slider",
            help="选择要删除的条文序号"
        )
        
        selected_row = df[df['id'] == st.session_state.delete_id]
        
        if not selected_row.empty:
            row_data = selected_row.iloc[0]
            st.markdown("---")
            st.markdown("**📋 预览将要删除的条文:**")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.info(f"**规范:** {row_data['规范']}")
                st.info(f"**条文号:** {row_data['条文']}")
            with col2:
                content_preview = row_data['条文内容'][:150] + "..." if len(row_data['条文内容']) > 150 else row_data['条文内容']
                st.text_area(
                    "条文内容预览",
                    value=content_preview,
                    height=100,
                    disabled=True,
                    key="delete_preview"
                )
            
            st.warning("⚠️ 此操作不可撤销,请确认后再删除!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ 确认删除", type="primary", use_container_width=True, key="confirm_delete"):
                    delete_row(st.session_state.delete_id)
                    st.session_state.show_delete_modal = False
                    st.success(f"✅ 已成功删除ID为 {st.session_state.delete_id} 的条文")
                    st.rerun()
            with col2:
                if st.button("取消", use_container_width=True, key="cancel_delete"):
                    st.session_state.show_delete_modal = False
                    st.rerun()
        else:
            st.error("❌ 未找到该ID对应的条文")
    
    render_modal_footer()

def show_insert_modal():
    """插入条文弹窗"""
    if not st.session_state.show_insert_modal:
        return
    

    st.markdown("**请填写新条文的完整信息:**")
    
    with st.form(key="insert_form", clear_on_submit=False):
        col1, col2 = st.columns([1, 1])
        with col1:
            new_specification = st.text_input(
                "📘 规范名称",
                value=st.session_state.last_spec,
                placeholder="例如: GB50016-2014",
                help="输入规范的完整名称"
            )
        with col2:
            new_article = st.text_input(
                "🔢 条文号",
                value="",
                placeholder="例如: 5.3.1A",
                help="输入条文的编号"
            )
        
        new_content = st.text_area(
            "📝 条文内容",
            value="",
            height=150,
            placeholder="请输入详细的条文内容...",
            help="输入条文的详细内容描述"
        )
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit_insert = st.form_submit_button(
                "✅ 确认插入",
                type="primary",
                use_container_width=True
            )
        with col3:
            cancel_insert = st.form_submit_button(
                "❌ 取消",
                use_container_width=True
            )
        
        if submit_insert:
            if not all([new_specification.strip(), new_article.strip(), new_content.strip()]):
                st.error("❌ 所有字段都不能为空!")
            else:
                insert_row({
                    '规范': new_specification.strip(),
                    '条文': new_article.strip(),
                    '条文内容': new_content.strip()
                })
                st.session_state.last_spec = new_specification.strip()
                st.session_state.show_insert_modal = False
                st.success(f"✅ 已成功插入条文: {new_article}")
                st.rerun()
        
        if cancel_insert:
            st.session_state.show_insert_modal = False
            st.rerun()
    
    render_modal_footer()

def show_edit_modal():
    """修改条文弹窗"""
    if not st.session_state.show_edit_modal:
        return
    
    df = st.session_state.df
    
    
    if df.empty:
        st.warning("⚠️ 当前没有可修改的条文")
        if st.button("关闭", key="close_empty_edit"):
            st.session_state.show_edit_modal = False
            st.rerun()
    else:
        st.markdown("**第一步: 选择要修改的条文**")
        
        selection_method = st.radio(
            "选择方式",
            ["通过ID滑动选择", "通过条文号搜索"],
            horizontal=True,
            key="edit_selection_method"
        )
        
        if selection_method == "通过ID滑动选择":
            edit_id = st.slider(
                "拖动选择条文ID",
                min_value=1,
                max_value=len(df),
                value=st.session_state.edit_id,
                key="edit_id_slider"
            )
        else:
            article_list = df['条文'].unique().tolist()
            selected_article = st.selectbox(
                "选择条文号",
                options=article_list,
                key="edit_article_select"
            )
            matched_row = df[df['条文'] == selected_article]
            edit_id = matched_row.iloc[0]['id'] if not matched_row.empty else 1
        
        st.session_state.edit_id = edit_id
        current_row = df[df['id'] == edit_id]
        
        if not current_row.empty:
            st.markdown("---")
            st.markdown("**第二步: 修改条文内容**")
            
            current_data = current_row.iloc[0]
            
            with st.form(key="edit_form"):
                col1, col2 = st.columns([1, 1])
                with col1:
                    edit_specification = st.text_input(
                        "📘 规范名称",
                        value=current_data['规范'],
                        key="edit_spec"
                    )
                with col2:
                    edit_article = st.text_input(
                        "🔢 条文号",
                        value=current_data['条文'],
                        key="edit_article"
                    )
                
                edit_content = st.text_area(
                    "📝 条文内容",
                    value=current_data['条文内容'],
                    height=150,
                    key="edit_content"
                )
                
                with st.expander("📊 查看修改对比", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**原始内容:**")
                        st.text(current_data['条文内容'][:200] + "...")
                    with col2:
                        st.markdown("**修改后内容:**")
                        st.text(edit_content[:200] + "...")
                
                st.markdown("---")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    submit_edit = st.form_submit_button(
                        "💾 保存修改",
                        type="primary",
                        use_container_width=True
                    )
                with col3:
                    cancel_edit = st.form_submit_button(
                        "❌ 取消",
                        use_container_width=True
                    )
                
                if submit_edit:
                    if not all([edit_specification.strip(), edit_article.strip(), edit_content.strip()]):
                        st.error("❌ 所有字段都不能为空!")
                    else:
                        update_row(edit_id, {
                            '规范': edit_specification.strip(),
                            '条文': edit_article.strip(),
                            '条文内容': edit_content.strip()
                        })
                        st.session_state.show_edit_modal = False
                        st.success(f"✅ 已成功修改ID为 {edit_id} 的条文")
                        st.rerun()
                
                if cancel_edit:
                    st.session_state.show_edit_modal = False
                    st.rerun()
        else:
            st.error("❌ 找不到指定ID的条文")
    
    render_modal_footer()

# ==================== 图谱建模页面 ====================
def show_graph_modeling():
    """显示图谱建模页面"""
    st.title("📊 知识图谱建模")
    
    # 控制面板
    with st.container():
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔨 从标注数据构建图谱", type="primary", use_container_width=True):
                st.session_state.knowledge_graph = build_knowledge_graph()
                st.success("✅ 知识图谱构建完成！")
                st.rerun()
        
        with col2:
            kg = st.session_state.knowledge_graph
            if kg['nodes']:
                json_data = json.dumps(kg, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📥 导出JSON",
                    data=json_data,
                    file_name=f"knowledge_graph_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                st.button("📥 导出JSON (需先构建)", disabled=True, use_container_width=True)
        
        with col3:
            if st.button("🗑️ 清空图谱", use_container_width=True):
                st.session_state.knowledge_graph = {'nodes': [], 'edges': [], 'rules': []}
                st.success("✅ 图谱已清空")
                st.rerun()
        
        with col4:
            if st.button("🔙 返回主页面", use_container_width=True):
                st.session_state.current_view = 'main'
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 显示图谱统计
    kg = st.session_state.knowledge_graph
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("🎯 实体数量", len(kg['nodes']))
    with col_stats2:
        st.metric("🔗 关系数量", len(kg['edges']))
    with col_stats3:
        st.metric("📜 规则数量", len(kg['rules']))
    
    # 图谱可视化
    if kg['nodes']:
        st.subheader("🕸️ 知识图谱可视化")
        
        try:
            # 创建NetworkX图
            G = nx.Graph()
            
            # 添加节点
            for node in kg['nodes']:
                G.add_node(node['id'], label=node['label'], title=str(node['properties']))
            
            # 添加边
            for edge in kg['edges']:
                if G.has_node(edge['source']) and G.has_node(edge['target']):
                    G.add_edge(edge['source'], edge['target'], title=edge['label'])
            
            # 创建Pyvis网络
            net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black", notebook=True)
            net.from_nx(G)
            
            # 设置物理引擎
            net.set_options("""
            {
                "physics": {
                    "enabled": true,
                    "stabilization": {"iterations": 100}
                },
                "nodes": {
                    "color": {"background": "#97C2FC", "border": "#2B7CE9"},
                    "font": {"size": 14}
                },
                "edges": {
                    "color": {"color": "#848484"},
                    "smooth": {"type": "continuous"}
                }
            }
            """)
            
            # 保存并显示
            html_file = "knowledge_graph.html"
            net.save_graph(html_file)
            
            # 允许用户开启"点击节点删除"功能，点击节点会弹出确认对话并删除节点
            enable_node_delete = st.checkbox(
                                "启用图上点击删除实体（点击节点将弹出确认并删除）",
                                value=False,
                                key="enable_node_delete"
                        )

            with open(html_file, 'r', encoding='utf-8') as f:
                                source_code = f.read()

                        # 如果开启删除功能，向生成的 HTML 注入 JS 逻辑
            if enable_node_delete:
                                delete_js = '''
<script>
// 等待 vis/network 对象初始化后绑定点击事件
if (typeof network !== 'undefined' && typeof nodes !== 'undefined') {
    network.on("click", function(params) {
        try {
            if (params.nodes && params.nodes.length === 1) {
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId) || {label: nodeId};
                var label = node.label || nodeId;
                var msg = '是否删除实体: ' + label + ' (ID: ' + nodeId + ')?';
                if (confirm(msg)) {
                    nodes.remove(nodeId);
                    // 也可以删除相关的边(vis 会自动处理)
                }
            }
        } catch (e) {
            console.error('删除节点脚本出错:', e);
        }
    });
}
</script>
'''
                                # 将脚本插入到 </body> 之前
            if "</body>" in source_code:
                                        source_code = source_code.replace("</body>", delete_js + "</body>")
            else:
                                        source_code = source_code + delete_js

            st.components.v1.html(source_code, height=620, scrolling=True)
            
        except Exception as e:
            st.error(f"❌ 图谱可视化失败: {e}")
    else:
            st.info("ℹ️ 暂无图谱数据，请先点击从标注数据构建图谱按钮")
    
    # 实体管理标签页
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📋 实体管理", "🔗 关系管理", "📜 规则管理"])
    
    with tab1:
        st.subheader("实体列表")
        if kg['nodes']:
            entity_df = pd.DataFrame(kg['nodes'])
            entity_df_display = entity_df[['id', 'label', 'type']].copy()
            entity_df_display.columns = ['ID', '实体名称', '类型']
            
            st.dataframe(
                entity_df_display,
                use_container_width=True,
                height=400,
                hide_index=True
            )
            
            # 实体详情展示
            with st.expander("🔍 查看实体详情", expanded=False):
                selected_entity_id = st.selectbox(
                    "选择实体ID",
                    options=entity_df['id'].tolist(),
                    format_func=lambda x: f"ID {x}: {entity_df[entity_df['id']==x]['label'].values[0]}"
                )
                
                if selected_entity_id:
                    entity_info = entity_df[entity_df['id'] == selected_entity_id].iloc[0]
                    st.json(entity_info.to_dict())
        else:
            st.info("📭 暂无实体数据")
    
    with tab2:
        st.subheader("关系列表")
        if kg['edges']:
            # 创建关系显示DataFrame
            relations_data = []
            for edge in kg['edges']:
                source_label = next((n['label'] for n in kg['nodes'] if n['id'] == edge['source']), '未知')
                target_label = next((n['label'] for n in kg['nodes'] if n['id'] == edge['target']), '未知')
                relations_data.append({
                    'ID': edge['id'],
                    '源实体': source_label,
                    '关系类型': edge['label'],
                    '目标实体': target_label,
                    '描述': edge.get('description', '')
                })
            
            relations_df = pd.DataFrame(relations_data)
            st.dataframe(
                relations_df,
                use_container_width=True,
                height=400,
                hide_index=True
            )
            
            # 关系统计
            st.markdown("**📊 关系类型统计:**")
            relation_counts = relations_df['关系类型'].value_counts()
            col1, col2 = st.columns([2, 1])
            with col1:
                st.bar_chart(relation_counts)
            with col2:
                for rel_type, count in relation_counts.items():
                    st.metric(rel_type, count)
        else:
            st.info("ostringstream> 暂无关系数据")
    
    with tab3:
        st.subheader("规则列表")
        if kg['rules']:
            # 分页显示规则
            rules_per_page = 5
            total_pages = (len(kg['rules']) - 1) // rules_per_page + 1
            
            if 'current_rule_page' not in st.session_state:
                st.session_state.current_rule_page = 1
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("⬅️ 上一页", disabled=(st.session_state.current_rule_page == 1)):
                    st.session_state.current_rule_page -= 1
                    st.rerun()
            with col2:
                st.markdown(f"<center>第 {st.session_state.current_rule_page} / {total_pages} 页</center>", unsafe_allow_html=True)
            with col3:
                if st.button("下一页 ➡️", disabled=(st.session_state.current_rule_page == total_pages)):
                    st.session_state.current_rule_page += 1
                    st.rerun()
            
            # 显示当前页的规则
            start_idx = (st.session_state.current_rule_page - 1) * rules_per_page
            end_idx = min(start_idx + rules_per_page, len(kg['rules']))
            
            for rule in kg['rules'][start_idx:end_idx]:
                with st.container():
                    st.markdown(f'<div class="rule-container">', unsafe_allow_html=True)
                    st.markdown(f"**规则 #{rule['id']}** | 来源: `{rule['source']}`")
                    st.write(rule['content'])
                    if rule['entities']:
                        st.markdown(f"**关联实体:** {' · '.join(rule['entities'])}")
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("ostringstream> 暂无规则数据")

# ==================== 主页面 ====================
def show_main_page():
    """显示主页面"""
    df = get_dataframe()
    
    st.title("Code Knowledge Graph Label Toolkit V4.2")
    st.markdown("**建筑设计规范 - 知识图谱标注工具**")
    st.markdown("---")

    # 工具栏区域
    col_search, col_actions, col_stats = st.columns([3, 4, 3], gap="medium")

    # 1. 左侧：条文定位与查找
    with col_search:
        st.subheader(" 条文定位 & 查找")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            filter_option = st.radio(
                "显示模式",
                ["显示全部", "只示已处理", "只示未处理"],
                index=0,
                key="filter_mode"
            )
        
        with c2:
            search_query = st.text_input("输入查找内容", placeholder="例如：甲类厂房")
        
        with c3:
            st.write("")
            st.write("")
            if st.button(" 查找", use_container_width=True):
                if search_query:
                    st.success(f"正在搜索: {search_query}")
                else:
                    st.warning("请输入搜索关键词")

    # 2. 中间：条文操作与建模
    with col_actions:
        st.subheader(" 条文操作")
        ac1, ac2, ac3, ac4 = st.columns(4)
        
        with ac1:
            if st.button(" 删除\n条文", use_container_width=True):
                st.session_state.show_delete_modal = True
                st.rerun()
            if st.button(" 修改\n序号", use_container_width=True):
                st.session_state.show_edit_modal = True
                st.rerun()
        
        with ac2:
            if st.button(" 插入\n条文", use_container_width=True):
                st.session_state.show_insert_modal = True
                st.rerun()
            st.button(" 拆解\n条文", use_container_width=True, disabled=True, help="功能开发中")
        
        with ac3:
            if st.button(" 图谱\n建模", type="primary", use_container_width=True, help="核心功能：生成知识图谱"):
                st.session_state.current_view = 'graph_modeling'
                st.rerun()
            st.button(" 重新\n建模", use_container_width=True, disabled=True, help="功能开发中")
        
        with ac4:
            st.button(" 标注\n规则", type="primary", use_container_width=True, disabled=True, help="功能开发中")
            st.button(" 重写\n规则", use_container_width=True, disabled=True, help="功能开发中")
    
    # 左上角导入模块
    with st.sidebar:
        st.header("  项目管理")
        
        if st.button(" 新建项目", type="primary", use_container_width=True):
            st.session_state.show_new_project_modal = True
            st.rerun()
        
        if st.button(" 打开项目", type="secondary", use_container_width=True):
            st.session_state.show_load_project_modal = True
            st.rerun()
        
        if st.session_state.current_project:
            st.info(f"**当前项目:** {st.session_state.current_project}")
            if st.button(" 导出项目", type="secondary", use_container_width=True):
                export_project()
        else:
            st.warning("⚠️ 未选择项目")
        
        st.markdown("---")
        st.header("  文件操作")
        
        if st.button("导入规范", type="primary", use_container_width=True):
            st.session_state.show_import_modal = True
            st.session_state.show_delete_modal = False
            st.session_state.show_add_modal = False
            st.session_state.show_edit_modal = False
        
        if st.button("导入本体", type="secondary", use_container_width=True):
            st.session_state.show_import_modal = True
            st.session_state.show_delete_modal = False
            st.session_state.show_add_modal = False
            st.session_state.show_edit_modal = False
        
        st.markdown("---")
        st.header("  本体操作")
        
        if st.button("本体管理", type="secondary", use_container_width=True):
            st.session_state.show_ontology_modal = True
            st.rerun()
        
        # 显示当前本体统计
        if st.session_state.knowledge_graph:
            st.markdown("**本体统计:**")
            st.caption(f"实体: {len(st.session_state.knowledge_graph.get('nodes', []))}")
            st.caption(f"关系: {len(st.session_state.knowledge_graph.get('edges', []))}")

    # 3. 右侧：标注统计
    with col_stats:
        st.subheader(" 标注统计")
        stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)
        
        total_items = len(df) if not df.empty else 0
        labeled_entities = len(df[df["实体标注"] == "√"]) if not df.empty else 0
        labeled_relations = len(df[df["关系标注"] == "√"]) if not df.empty else 0
        labeled_rules = len(df[df["规则标注"] == "√"]) if not df.empty else 0
        
        with stat_c1:
            st.markdown(render_stat_box("总条文", total_items), unsafe_allow_html=True)
        with stat_c2:
            st.markdown(render_stat_box("已标注实体", labeled_entities), unsafe_allow_html=True)
        with stat_c3:
            st.markdown(render_stat_box("已标注关系", labeled_relations), unsafe_allow_html=True)
        with stat_c4:
            st.markdown(render_stat_box("已处理规则", labeled_rules), unsafe_allow_html=True)

    st.markdown("---")

    # 数据处理逻辑
    if not df.empty:
        display_df = df.copy()

        # 过滤逻辑
        if filter_option == "只示已处理":
            display_df = display_df[display_df["规则标注"] == "√"]
        elif filter_option == "只示未处理":
            display_df = display_df[display_df["规则标注"] != "√"]

        # 搜索逻辑
        if search_query:
            display_df = display_df[
                display_df["条文内容"].astype(str).str.contains(search_query, case=False, na=False) | 
                display_df["条文"].astype(str).str.contains(search_query, case=False, na=False)
            ]
    else:
        display_df = pd.DataFrame(columns=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])

    # 主数据表格
    column_config = {
        "id": st.column_config.NumberColumn("ID", width="small"),
        "规范": st.column_config.TextColumn("规范名称", width="medium"),
        "条文": st.column_config.TextColumn("条文号", width="small"),
        "条文内容": st.column_config.TextColumn("条文内容", width="large"),
        "实体标注": st.column_config.CheckboxColumn("实体", width="small"),
        "关系标注": st.column_config.CheckboxColumn("关系", width="small"),
        "规则标注": st.column_config.CheckboxColumn("规则", width="small"),
    }

    st.dataframe(
        display_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=700,
        key='main_data_editor'
    )

    # 底部状态栏
    if st.session_state.current_project:
        st.caption(f"📊 当前项目: {st.session_state.current_project} | 共加载 {len(display_df)} 条数据 | ✅ 系统状态: 就绪")
    else:
        st.caption(f"📊 当前共加载 {len(display_df)} 条数据 | ✅ 系统状态: 就绪 | 📁 未选择项目")

# ==================== 主程序入口 ====================
def main():
    """主程序入口"""
    # 显示弹窗
    show_import_modal()
    show_new_project_modal()
    show_load_project_modal()
    show_ontology_modal()
    show_delete_modal()
    show_insert_modal()
    show_edit_modal()
    
    # 快捷键提示
    if any([st.session_state.show_delete_modal, 
            st.session_state.show_insert_modal, 
            st.session_state.show_edit_modal,
            st.session_state.show_import_modal,
            st.session_state.show_new_project_modal,
            st.session_state.show_load_project_modal,
            st.session_state.show_ontology_modal]):
        st.markdown("""
        <div style="position: fixed; bottom: 20px; right: 20px; 
                    background: rgba(0,0,0,0.7); color: white; 
                    padding: 10px 15px; border-radius: 5px; font-size: 12px;
                    z-index: 9999;">
            💡 提示: 按 ESC 键快速关闭弹窗
        </div>
        """, unsafe_allow_html=True)
    
    # 页面路由
    if st.session_state.current_view == 'graph_modeling':
        show_graph_modeling()
    else:
        show_main_page()

# 运行主程序
if __name__ == "__main__":
    main()