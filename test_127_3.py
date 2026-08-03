import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import zipfile
from io import BytesIO, StringIO
import os

# ================ 新增知识图谱可视化库 ================
try:
    from pyvis.network import Network
    import networkx as nx
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False
    st.warning("⚠️ 未安装 pyvis 和 networkx 库，知识图谱可视化功能将不可用。请运行：pip install pyvis networkx")

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="建筑设计规范 - 知识图谱标注工具",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🏗️"
)

# ==================== 自定义样式 ====================
def load_custom_css():
    """加载自定义CSS样式"""
    st.markdown("""
        <style>
            /* 主容器样式 */
            .block-container {
                padding-top: 1rem;
                padding-bottom: 1rem;
            }
            
            /* 数据表格样式 */
            .stDataFrame {
                font-size: 14px;
            }
            
            /* 统计盒子样式 */
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                color: white;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin: 5px 0;
            }
            .stat-box h3 {
                margin: 0;
                font-size: 2rem;
                font-weight: bold;
            }
            .stat-box p {
                margin: 5px 0 0 0;
                font-size: 0.9rem;
                opacity: 0.9;
            }
            
            /* 卡片样式 */
            .card {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 20px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            
            /* 项目卡片样式 */
            .project-card {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0;
                transition: all 0.3s ease;
            }
            .project-card:hover {
                background-color: #e9ecef;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            
            /* 弹窗样式 */
            div[data-testid="stExpander"] {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
            
            /* 进度条样式 */
            .stProgress > div > div {
                background-color: #667eea;
            }
            
            /* 侧边栏样式 */
            .css-1d391kg {
                background-color: #f8f9fa;
            }
            
            /* 按钮悬停效果 */
            .stButton > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }
            
            /* 知识图谱节点样式 */
            .kg-node {
                display: inline-block;
                background-color: #e3f2fd;
                border: 2px solid #2196f3;
                border-radius: 20px;
                padding: 5px 15px;
                margin: 5px;
                font-size: 14px;
            }
            .kg-edge {
                display: inline-block;
                background-color: #fff3e0;
                border: 2px solid #ff9800;
                border-radius: 20px;
                padding: 5px 15px;
                margin: 5px;
                font-size: 14px;
            }
        </style>
    """, unsafe_allow_html=True)

def render_stat_box(label, value, color="blue"):
    """渲染统计盒子"""
    colors = {
        "blue": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "green": "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)",
        "orange": "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
        "purple": "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
    }
    bg = colors.get(color, colors["blue"])
    return f"""
        <div style="background: {bg}; border-radius: 10px; padding: 20px; text-align: center; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h3 style="margin: 0; font-size: 2rem; font-weight: bold;">{value}</h3>
            <p style="margin: 5px 0 0 0; font-size: 0.9rem; opacity: 0.9;">{label}</p>
        </div>
    """

# ==================== Session State 初始化 ====================
def init_session_state():
    """初始化所有会话状态变量"""
    defaults = {
        # 项目管理
        'projects': {},
        'current_project': None,
        'current_project_path': None,
        
        # 数据
        'df': pd.DataFrame(columns=["规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"]),
        'knowledge_graph': {'nodes': [], 'edges': [], 'rules': []},
        
        # 视图控制
        'current_view': 'main',
        
        # 弹窗控制
        'show_import_modal': False,
        'show_new_project_modal': False,
        'show_load_project_modal': False,
        'show_ontology_modal': False,
        'show_delete_modal': False,
        'show_add_modal': False,
        'show_edit_modal': False,
        'show_node_modal': False,
        'show_edge_modal': False,
        
        # 选中状态
        'selected_rows': [],
        'selected_node': None,
        'selected_edge': None,
        
        # 过滤
        'filter_option': '全部',
        'search_text': '',
        
        # 图谱可视化相关
        'kg_visualization_settings': {
            'node_size': 20,
            'edge_width': 2,
            'physics_enabled': True,
            'show_labels': True
        }
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
        'updated_at': datetime.now().isoformat(),
        'data': [],
        'ontology': {'nodes': [], 'edges': [], 'rules': []}
    }
    
    st.session_state.projects[project_name] = project_data
    st.session_state.current_project = project_name
    st.session_state.df = pd.DataFrame(columns=["规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
    st.session_state.knowledge_graph = {'nodes': [], 'edges': [], 'rules': []}
    
    return True, f"✅ 项目 '{project_name}' 创建成功！"

def load_project(project_name: str) -> bool:
    """加载项目"""
    if project_name not in st.session_state.projects:
        return False
    
    project_data = st.session_state.projects[project_name]
    st.session_state.current_project = project_name
    
    if project_data.get('data'):
        st.session_state.df = pd.DataFrame(project_data['data'])
        # 确保标注列存在
        for col in ["实体标注", "关系标注", "规则标注"]:
            if col not in st.session_state.df.columns:
                st.session_state.df[col] = False
    else:
        st.session_state.df = pd.DataFrame(columns=["规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
    
    st.session_state.knowledge_graph = project_data.get('ontology', {'nodes': [], 'edges': [], 'rules': []})
    return True

def save_current_project():
    """保存当前项目"""
    if st.session_state.current_project:
        project_name = st.session_state.current_project
        st.session_state.projects[project_name]['data'] = st.session_state.df.to_dict('records')
        st.session_state.projects[project_name]['ontology'] = st.session_state.knowledge_graph
        st.session_state.projects[project_name]['updated_at'] = datetime.now().isoformat()

def delete_project(project_name: str) -> bool:
    """删除项目"""
    if project_name in st.session_state.projects:
        del st.session_state.projects[project_name]
        if st.session_state.current_project == project_name:
            st.session_state.current_project = None
            st.session_state.df = pd.DataFrame(columns=["规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"])
            st.session_state.knowledge_graph = {'nodes': [], 'edges': [], 'rules': []}
        return True
    return False

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
        # 保存项目配置
        zf.writestr('project.json', json.dumps(project_data, ensure_ascii=False, indent=2))
        # 保存数据CSV
        if not st.session_state.df.empty:
            csv_data = st.session_state.df.to_csv(index=False, encoding='utf-8-sig')
            zf.writestr('clauses.csv', csv_data)
        # 保存本体
        zf.writestr('ontology.json', json.dumps(st.session_state.knowledge_graph, ensure_ascii=False, indent=2))
    
    zip_buffer.seek(0)
    st.download_button(
        label="⬇️ 点击下载项目包",
        data=zip_buffer,
        file_name=f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True
    )

# ==================== 智能列识别函数 ====================
def guess_column_mapping(columns: list) -> dict:
    """智能猜测列映射关系"""
    mapping = {
        '规范': None,
        '条文': None,
        '条文内容': None
    }
    
    rules = {
        '规范': ['规范名称', '规范', '标准名称', '标准', 'standard', 'spec', '文件名', '规范编号'],
        '条文': ['条文号', '条文编号', '章节号', '编号', '条款号', 'article', 'clause', 'section', '序号', '条文'],
        '条文内容': ['条文内容', '内容', '正文', '条款内容', 'content', 'text', '描述', '说明', '条款']
    }
    
    columns_lower = [str(c).lower().strip() for c in columns]
    used_columns = set()
    
    for target, keywords in rules.items():
        for keyword in keywords:
            for i, col in enumerate(columns_lower):
                if keyword.lower() in col and columns[i] not in used_columns:
                    mapping[target] = columns[i]
                    used_columns.add(columns[i])
                    break
            if mapping[target]:
                break
    
    # 如果还有未匹配的，按列顺序自动分配
    unmapped_cols = [c for c in columns if c not in used_columns]
    unmapped_targets = [t for t, v in mapping.items() if v is None]
    
    for i, target in enumerate(unmapped_targets):
        if i < len(unmapped_cols):
            mapping[target] = unmapped_cols[i]
    
    return mapping

def read_file_with_encoding(uploaded_file) -> pd.DataFrame:
    """尝试多种编码读取文件"""
    content = uploaded_file.getvalue()
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1']
    
    for encoding in encodings:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(BytesIO(content), encoding=encoding)
            elif uploaded_file.name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(BytesIO(content))
            else:
                df = pd.read_csv(BytesIO(content), encoding=encoding)
            
            if len(df.columns) >= 1 and len(df) >= 1:
                return df
        except Exception:
            continue
    
    raise ValueError("无法识别文件编码，请检查文件格式")

def apply_column_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """应用列映射，生成标准格式的DataFrame"""
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

# ==================== 数据导入函数 ====================
def import_from_json(uploaded_file) -> bool:
    """从JSON导入数据"""
    try:
        data = json.load(uploaded_file)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict) and 'data' in data:
            df = pd.DataFrame(data['data'])
        else:
            st.error("❌ JSON格式不正确")
            return False
        
        # 智能映射列
        mapping = guess_column_mapping(list(df.columns))
        result_df = apply_column_mapping(df, mapping)
        
        st.session_state.df = result_df
        save_current_project()
        return True
    except Exception as e:
        st.error(f"❌ 导入失败: {str(e)}")
        return False

def import_ontology(uploaded_file) -> bool:
    """导入本体文件"""
    try:
        ontology_data = json.load(uploaded_file)
        
        # 确保基本结构存在
        if 'nodes' not in ontology_data:
            ontology_data = {'nodes': [], 'edges': [], 'rules': [], 'raw': ontology_data}
        if 'edges' not in ontology_data:
            ontology_data['edges'] = []
        if 'rules' not in ontology_data:
            ontology_data['rules'] = []
            
        st.session_state.knowledge_graph = ontology_data
        save_current_project()
        return True
    except Exception as e:
        st.error(f"❌ 导入本体失败: {str(e)}")
        return False

# ==================== 知识图谱操作函数 ====================
def add_node(node_id: str, node_type: str = "实体", properties: dict = None):
    """添加节点"""
    if 'nodes' not in st.session_state.knowledge_graph:
        st.session_state.knowledge_graph['nodes'] = []
    
    # 检查是否已存在
    existing_ids = [n.get('id') for n in st.session_state.knowledge_graph['nodes']]
    if node_id in existing_ids:
        return False, "节点已存在"
    
    node = {
        'id': node_id,
        'label': node_id,
        'type': node_type,
        'properties': properties or {},
        'created_at': datetime.now().isoformat()
    }
    st.session_state.knowledge_graph['nodes'].append(node)
    save_current_project()
    return True, "节点添加成功"

def delete_node(node_id: str):
    """删除节点及相关边"""
    if 'nodes' not in st.session_state.knowledge_graph:
        return False
    
    # 删除节点
    st.session_state.knowledge_graph['nodes'] = [
        n for n in st.session_state.knowledge_graph['nodes'] if n.get('id') != node_id
    ]
    
    # 删除相关边
    if 'edges' in st.session_state.knowledge_graph:
        st.session_state.knowledge_graph['edges'] = [
            e for e in st.session_state.knowledge_graph['edges']
            if e.get('source') != node_id and e.get('target') != node_id
        ]
    
    save_current_project()
    return True

def add_edge(source: str, target: str, relation: str, properties: dict = None):
    """添加边（关系）"""
    if 'edges' not in st.session_state.knowledge_graph:
        st.session_state.knowledge_graph['edges'] = []
    
    edge = {
        'id': f"{source}_{relation}_{target}",
        'source': source,
        'target': target,
        'relation': relation,
        'properties': properties or {},
        'created_at': datetime.now().isoformat()
    }
    st.session_state.knowledge_graph['edges'].append(edge)
    save_current_project()
    return True

def delete_edge(edge_id: str):
    """删除边"""
    if 'edges' not in st.session_state.knowledge_graph:
        return False
    
    st.session_state.knowledge_graph['edges'] = [
        e for e in st.session_state.knowledge_graph['edges'] if e.get('id') != edge_id
    ]
    save_current_project()
    return True

def add_rule(rule_name: str, rule_content: str, rule_type: str = "约束规则"):
    """添加规则"""
    if 'rules' not in st.session_state.knowledge_graph:
        st.session_state.knowledge_graph['rules'] = []
    
    rule = {
        'id': f"rule_{len(st.session_state.knowledge_graph['rules']) + 1}",
        'name': rule_name,
        'content': rule_content,
        'type': rule_type,
        'created_at': datetime.now().isoformat()
    }
    st.session_state.knowledge_graph['rules'].append(rule)
    save_current_project()
    return True

# ==================== 知识图谱可视化函数 ====================
def create_knowledge_graph_visualization():
    """创建知识图谱可视化"""
    if not PYVIS_AVAILABLE:
        st.error("❌ 请先安装 pyvis 和 networkx 库: pip install pyvis networkx")
        return None
    
    kg = st.session_state.knowledge_graph
    if not kg.get('nodes') and not kg.get('edges'):
        st.info("📭 暂无节点或边数据，无法生成可视化图谱")
        return None
    
    # 创建 Network 对象
    net = Network(
        height="600px", 
        width="100%", 
        bgcolor="#f0f0f0", 
        font_color="black",
        directed=True
    )
    
    # 设置物理引擎
    if st.session_state.kg_visualization_settings.get('physics_enabled', True):
        net.set_options("""
        var options = {
          "physics": {
            "enabled": true,
            "stabilization": {"iterations": 100}
          }
        }
        """)
    else:
        net.set_options("""
        var options = {
          "physics": {
            "enabled": false
          }
        }
        """)
    
    # 添加节点
    node_types = set(node.get('type', '实体') for node in kg.get('nodes', []))
    color_map = {}
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
    
    for i, node_type in enumerate(node_types):
        color_map[node_type] = colors[i % len(colors)]
    
    for node in kg.get('nodes', []):
        node_id = node.get('id', node.get('label', ''))
        node_type = node.get('type', '实体')
        color = color_map.get(node_type, '#95a5a6')
        
        net.add_node(
            node_id,
            label=node.get('label', node_id) if st.session_state.kg_visualization_settings.get('show_labels', True) else '',
            color=color,
            title=f"类型: {node_type}\n{node.get('properties', {}).get('description', '')}",
            size=st.session_state.kg_visualization_settings.get('node_size', 20)
        )
    
    # 添加边
    for edge in kg.get('edges', []):
        net.add_edge(
            edge.get('source', ''),
            edge.get('target', ''),
            label=edge.get('relation', ''),
            title=f"关系: {edge.get('relation', '')}",
            width=st.session_state.kg_visualization_settings.get('edge_width', 2)
        )
    
    return net

def show_knowledge_graph_visualization():
    """显示知识图谱可视化"""
    if not PYVIS_AVAILABLE:
        st.error("❌ 请先安装 pyvis 和 networkx 库: pip install pyvis networkx")
        return
    
    st.markdown("### 🗺️ 知识图谱可视化")
    
    # 可视化设置
    with st.expander("⚙️ 可视化设置", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            node_size = st.slider("节点大小", 10, 50, st.session_state.kg_visualization_settings.get('node_size', 20))
            st.session_state.kg_visualization_settings['node_size'] = node_size
        
        with col2:
            edge_width = st.slider("边宽度", 1, 10, st.session_state.kg_visualization_settings.get('edge_width', 2))
            st.session_state.kg_visualization_settings['edge_width'] = edge_width
        
        with col3:
            show_labels = st.checkbox("显示标签", value=st.session_state.kg_visualization_settings.get('show_labels', True))
            st.session_state.kg_visualization_settings['show_labels'] = show_labels
        
        with col4:
            physics_enabled = st.checkbox("启用物理引擎", value=st.session_state.kg_visualization_settings.get('physics_enabled', True))
            st.session_state.kg_visualization_settings['physics_enabled'] = physics_enabled
    
    # 生成并显示图谱
    net = create_knowledge_graph_visualization()
    if net:
        try:
            # 保存为 HTML 并显示
            path = "temp_kg.html"
            net.save_graph(path)
            
            with open(path, 'r', encoding='utf-8') as f:
                html_string = f.read()
            
            # 显示图谱
            components = st.components.v1
            components.html(html_string, height=600, scrolling=True)
            
            # 提供下载选项
            with open(path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            st.download_button(
                label="💾 下载可视化图谱 (HTML)",
                data=html_content,
                file_name="knowledge_graph.html",
                mime="text/html",
                use_container_width=True
            )
            
            # 清理临时文件
            import os
            if os.path.exists(path):
                os.remove(path)
                
        except Exception as e:
            st.error(f"❌ 可视化生成失败: {str(e)}")
    else:
        st.info("📭 暂无数据可可视化")

# ==================== 导入弹窗 ====================
def show_import_modal():
    """导入规范弹窗 - 支持任意CSV自动映射"""
    if not st.session_state.show_import_modal:
        return
    
    with st.expander("📥 智能导入数据", expanded=True):
        st.markdown("### 📄 上传规范文件")
        st.info("💡 支持任意格式的CSV/Excel文件，系统会自动识别并映射列")
        
        # 选择导入类型
        import_type = st.radio(
            "选择导入类型",
            ["📄 规范条文", "🧠 本体文件"],
            horizontal=True,
            key="import_type_radio"
        )
        
        if import_type == "📄 规范条文":
            uploaded_file = st.file_uploader(
                "选择文件",
                type=['csv', 'xlsx', 'xls'],
                key="smart_uploader",
                help="支持CSV、Excel格式，任意列名都可以"
            )
            
            if uploaded_file:
                try:
                    df = read_file_with_encoding(uploaded_file)
                    st.success(f"✅ 文件读取成功！共 {len(df)} 行, {len(df.columns)} 列")
                    
                    with st.expander("📋 原始数据预览（前5行）", expanded=False):
                        st.dataframe(df.head(), use_container_width=True)
                    
                    st.markdown("---")
                    st.markdown("### 🔄 列映射配置")
                    
                    auto_mapping = guess_column_mapping(list(df.columns))
                    all_columns = ['(不选择)'] + list(df.columns)
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**📘 规范名称**")
                        default_idx_1 = all_columns.index(auto_mapping['规范']) if auto_mapping['规范'] in all_columns else 0
                        col_spec = st.selectbox("规范列", all_columns, index=default_idx_1, key="map_spec", label_visibility="collapsed")
                    
                    with col2:
                        st.markdown("**📑 条文号**")
                        default_idx_2 = all_columns.index(auto_mapping['条文']) if auto_mapping['条文'] in all_columns else 0
                        col_clause = st.selectbox("条文列", all_columns, index=default_idx_2, key="map_clause", label_visibility="collapsed")
                    
                    with col3:
                        st.markdown("**📝 条文内容**")
                        default_idx_3 = all_columns.index(auto_mapping['条文内容']) if auto_mapping['条文内容'] in all_columns else 0
                        col_content = st.selectbox("内容列", all_columns, index=default_idx_3, key="map_content", label_visibility="collapsed")
                    
                    final_mapping = {
                        '规范': col_spec if col_spec != '(不选择)' else None,
                        '条文': col_clause if col_clause != '(不选择)' else None,
                        '条文内容': col_content if col_content != '(不选择)' else None
                    }
                    
                    st.markdown("---")
                    st.markdown("### 👁️ 转换预览")
                    
                    preview_df = apply_column_mapping(df, final_mapping)
                    st.dataframe(preview_df.head(10)[['规范', '条文', '条文内容']], use_container_width=True, hide_index=True)
                    st.caption(f"预览前10行，共 {len(preview_df)} 条数据")
                    
                    st.markdown("---")
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        if st.button("✅ 确认导入", type="primary", use_container_width=True):
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
            else:
                show_import_help()
        
        else:  # 本体文件
            uploaded_onto = st.file_uploader("上传本体文件", type=['json'], key="onto_uploader")
            if uploaded_onto:
                try:
                    onto_preview = json.load(uploaded_onto)
                    uploaded_onto.seek(0)
                    
                    st.markdown("### 👁️ 本体预览")
                    st.json(onto_preview)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ 确认导入", type="primary", use_container_width=True, key="import_onto_confirm"):
                            if import_ontology(uploaded_onto):
                                st.session_state.show_import_modal = False
                                st.success("✅ 本体导入成功！")
                                st.rerun()
                    with col2:
                        if st.button("❌ 取消", use_container_width=True, key="import_onto_cancel"):
                            st.session_state.show_import_modal = False
                            st.rerun()
                except Exception as e:
                    st.error(f"解析失败: {e}")
            else:
                st.info("📋 请上传JSON格式的本体文件")
        
        st.markdown("---")
        if st.button("❌ 关闭窗口", key="close_import", use_container_width=True):
            st.session_state.show_import_modal = False
            st.rerun()

def show_import_help():
    """显示导入帮助信息"""
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
    
    example_data = pd.DataFrame({
        "标准名": ["GB50016-2014", "GB50016-2014"],
        "章节": ["5.1.1", "5.1.2"],
        "内容描述": ["建筑高度大于27m的住宅建筑...", "建筑高度大于100m的民用建筑..."]
    })
    st.dataframe(example_data, use_container_width=True, hide_index=True)
    st.caption("系统会自动识别并映射为: 规范、条文、条文内容")

# ==================== 项目管理弹窗 ====================
def show_new_project_modal():
    """新建项目弹窗"""
    if not st.session_state.show_new_project_modal:
        return
    
    with st.expander("🆕 新建项目", expanded=True):
        st.markdown("### 创建新的标注项目")
        
        with st.form(key="new_project_form"):
            project_name = st.text_input(
                "项目名称",
                placeholder="请输入项目名称，例如：GB50016标注项目",
                key="new_project_name_input"
            )
            
            project_desc = st.text_area(
                "项目描述（可选）",
                placeholder="描述项目的目标和范围...",
                height=100,
                key="new_project_desc"
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
    
    with st.expander("📂 项目管理", expanded=True):
        projects = list(st.session_state.projects.keys())
        
        if projects:
            st.markdown("### 选择项目")
            
            for proj_name in projects:
                proj_data = st.session_state.projects[proj_name]
                data_count = len(proj_data.get('data', []))
                node_count = len(proj_data.get('ontology', {}).get('nodes', []))
                created = proj_data.get('created_at', '未知')[:10]
                
                col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                
                with col1:
                    st.markdown(f"**📁 {proj_name}**")
                    st.caption(f"创建于: {created}")
                
                with col2:
                    st.metric("条文", data_count)
                
                with col3:
                    st.metric("节点", node_count)
                
                with col4:
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("📂 打开", key=f"load_{proj_name}", use_container_width=True):
                            if load_project(proj_name):
                                st.session_state.show_load_project_modal = False
                                st.success(f"✅ 项目 '{proj_name}' 加载成功！")
                                st.rerun()
                    with btn_col2:
                        if st.button("🗑️", key=f"del_{proj_name}", use_container_width=True):
                            if delete_project(proj_name):
                                st.success(f"已删除项目: {proj_name}")
                                st.rerun()
                
                st.markdown("---")
            
            # 导入项目包
            st.markdown("### 📦 导入项目包")
            uploaded_zip = st.file_uploader("上传项目ZIP文件", type=['zip'], key="import_project_zip")
            if uploaded_zip:
                try:
                    with zipfile.ZipFile(BytesIO(uploaded_zip.read()), 'r') as zf:
                        if 'project.json' in zf.namelist():
                            project_data = json.loads(zf.read('project.json').decode('utf-8'))
                            proj_name = project_data.get('name', f"导入项目_{datetime.now().strftime('%H%M%S')}")
                            
                            # 避免重名
                            original_name = proj_name
                            counter = 1
                            while proj_name in st.session_state.projects:
                                proj_name = f"{original_name}_{counter}"
                                counter += 1
                            
                            project_data['name'] = proj_name
                            st.session_state.projects[proj_name] = project_data
                            st.success(f"✅ 项目 '{proj_name}' 导入成功！")
                            st.rerun()
                        else:
                            st.error("无效的项目包：缺少 project.json")
                except Exception as e:
                    st.error(f"导入失败: {str(e)}")
        else:
            st.info("📭 当前没有可用项目")
            st.markdown("点击下方按钮创建您的第一个项目")
            
            if st.button("🆕 创建新项目", type="primary", use_container_width=True):
                st.session_state.show_new_project_modal = True
                st.session_state.show_load_project_modal = False
                st.rerun()
        
        st.markdown("---")
        if st.button("❌ 关闭", key="close_load", use_container_width=True):
            st.session_state.show_load_project_modal = False
            st.rerun()

# ==================== 本体管理弹窗 ====================
def show_ontology_modal():
    """本体操作弹窗"""
    if not st.session_state.show_ontology_modal:
        return
    
    with st.expander("🧠 本体管理", expanded=True):
        kg = st.session_state.knowledge_graph
        
        # 统计信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(render_stat_box("实体节点", len(kg.get('nodes', [])), "blue"), unsafe_allow_html=True)
        with col2:
            st.markdown(render_stat_box("关系边", len(kg.get('edges', [])), "green"), unsafe_allow_html=True)
        with col3:
            st.markdown(render_stat_box("规则", len(kg.get('rules', [])), "orange"), unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 标签页
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ 添加节点", "🔗 添加关系", "📜 添加规则", "📋 查看本体", "📤 导入导出"])
        
        with tab1:
            st.markdown("### 添加实体节点")
            with st.form("add_node_form"):
                node_name = st.text_input("节点名称", placeholder="例如：建筑高度")
                node_type = st.selectbox("节点类型", ["实体", "属性", "概念", "约束", "其他"])
                node_desc = st.text_area("节点描述（可选）", placeholder="描述该节点的含义...", height=80)
                
                if st.form_submit_button("➕ 添加节点", type="primary", use_container_width=True):
                    if node_name.strip():
                        success, msg = add_node(
                            node_name.strip(),
                            node_type,
                            {'description': node_desc}
                        )
                        if success:
                            st.success(f"✅ 节点 '{node_name}' 添加成功！")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                    else:
                        st.error("❌ 节点名称不能为空")
        
        with tab2:
            st.markdown("### 添加关系边")
            nodes = kg.get('nodes', [])
            if len(nodes) < 2:
                st.warning("⚠️ 需要至少2个节点才能创建关系")
            else:
                node_names = [n.get('id', n.get('label', '')) for n in nodes]
                
                with st.form("add_edge_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        source = st.selectbox("源节点", node_names, key="edge_source")
                    with col2:
                        target = st.selectbox("目标节点", node_names, key="edge_target")
                    
                    relation = st.text_input("关系类型", placeholder="例如：属于、包含、大于等")
                    edge_desc = st.text_area("关系描述（可选）", height=60)
                    
                    if st.form_submit_button("🔗 添加关系", type="primary", use_container_width=True):
                        if source and target and relation.strip():
                            if source == target:
                                st.error("❌ 源节点和目标节点不能相同")
                            else:
                                add_edge(source, target, relation.strip(), {'description': edge_desc})
                                st.success(f"✅ 关系 '{source} --{relation}--> {target}' 添加成功！")
                                st.rerun()
                        else:
                            st.error("❌ 请填写完整信息")
        
        with tab3:
            st.markdown("### 添加规则")
            with st.form("add_rule_form"):
                rule_name = st.text_input("规则名称", placeholder="例如：高层建筑高度约束")
                rule_type = st.selectbox("规则类型", ["约束规则", "推理规则", "计算规则", "验证规则", "其他"])
                rule_content = st.text_area(
                    "规则内容",
                    placeholder="描述规则的具体内容...\n例如：IF 建筑高度 > 27m THEN 属于 高层建筑",
                    height=120
                )
                
                if st.form_submit_button("📜 添加规则", type="primary", use_container_width=True):
                    if rule_name.strip() and rule_content.strip():
                        add_rule(rule_name.strip(), rule_content.strip(), rule_type)
                        st.success(f"✅ 规则 '{rule_name}' 添加成功！")
                        st.rerun()
                    else:
                        st.error("❌ 规则名称和内容不能为空")
        
        with tab4:
            st.markdown("### 当前本体结构")
            
            # 节点列表
            if kg.get('nodes'):
                st.markdown("**📍 节点列表**")
                for i, node in enumerate(kg['nodes']):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        node_type = node.get('type', '实体')
                        st.markdown(f"<span class='kg-node'>🔹 {node.get('label', node.get('id'))} ({node_type})</span>", unsafe_allow_html=True)
                    with col2:
                        st.caption(node.get('created_at', '')[:10] if node.get('created_at') else '')
                    with col3:
                        if st.button("🗑️", key=f"del_node_{i}"):
                            delete_node(node.get('id'))
                            st.rerun()
            else:
                st.info("暂无节点")
            
            st.markdown("---")
            
            # 关系列表
            if kg.get('edges'):
                st.markdown("**🔗 关系列表**")
                for i, edge in enumerate(kg['edges']):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"<span class='kg-edge'>🔸 {edge.get('source')} --[{edge.get('relation')}]--> {edge.get('target')}</span>", unsafe_allow_html=True)
                    with col2:
                        if st.button("🗑️", key=f"del_edge_{i}"):
                            delete_edge(edge.get('id'))
                            st.rerun()
            else:
                st.info("暂无关系")
            
            st.markdown("---")
            
            # 规则列表
            if kg.get('rules'):
                st.markdown("**📜 规则列表**")
                for i, rule in enumerate(kg['rules']):
                    with st.expander(f"📋 {rule.get('name')} ({rule.get('type', '规则')})"):
                        st.write(rule.get('content', ''))
                        if st.button("🗑️ 删除此规则", key=f"del_rule_{i}"):
                            st.session_state.knowledge_graph['rules'].pop(i)
                            save_current_project()
                            st.rerun()
            else:
                st.info("暂无规则")
        
        with tab5:
            st.markdown("### 导入导出本体")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📥 导入本体**")
                uploaded_onto = st.file_uploader("上传本体JSON", type=['json'], key="modal_onto_upload")
                if uploaded_onto:
                    if st.button("确认导入", type="primary", use_container_width=True):
                        if import_ontology(uploaded_onto):
                            st.success("✅ 本体导入成功！")
                            st.rerun()
            
            with col2:
                st.markdown("**📤 导出本体**")
                onto_json = json.dumps(kg, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ 下载本体JSON",
                    data=onto_json,
                    file_name=f"ontology_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            st.markdown("---")
            
            # 清空本体
            if st.button("🗑️ 清空所有本体数据", type="secondary", use_container_width=True):
                st.session_state.knowledge_graph = {'nodes': [], 'edges': [], 'rules': []}
                save_current_project()
                st.success("✅ 本体已清空")
                st.rerun()
        
        st.markdown("---")
        if st.button("❌ 关闭", key="close_ontology", use_container_width=True):
            st.session_state.show_ontology_modal = False
            st.rerun()

# ==================== 搜索和筛选功能 ====================
def show_search_filter():
    """显示搜索和筛选功能"""
    if st.session_state.df.empty:
        return None
    
    with st.expander("🔍 搜索与筛选", expanded=False):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_text = st.text_input(
                "搜索内容",
                value=st.session_state.get('search_text', ''),
                placeholder="输入关键词搜索...",
                key="search_input"
            )
            st.session_state.search_text = search_text
        
        with col2:
            filter_option = st.selectbox(
                "筛选条件",
                ["全部", "已标注实体", "未标注实体", "已标注关系", "未标注关系", "已标注规则", "未标注规则"],
                key="filter_select"
            )
            st.session_state.filter_option = filter_option
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 重置筛选", use_container_width=True):
                st.session_state.search_text = ''
                st.session_state.filter_option = '全部'
                st.rerun()
    
    # 应用筛选
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
    
    return filtered_df

# ==================== 批量操作功能 ====================
def show_batch_operations():
    """显示批量操作选项"""
    if st.session_state.df.empty:
        return
    
    with st.expander("⚡ 批量操作", expanded=False):
        st.markdown("**快速标注**")
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
        
        st.markdown("**清除标注**")
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

# ==================== 图谱建模页面 ====================
def show_graph_modeling():
    """显示图谱建模页面"""
    st.markdown("## 🕸️ 知识图谱建模")
    
    # 顶部操作栏
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        if st.button("⬅️ 返回主页", type="secondary", use_container_width=True):
            st.session_state.current_view = 'main'
            st.rerun()
    
    with col2:
        if st.button("🧠 本体管理", type="primary", use_container_width=True):
            st.session_state.show_ontology_modal = True
            st.rerun()
    
    with col3:
        onto_json = json.dumps(st.session_state.knowledge_graph, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 导出本体",
            data=onto_json,
            file_name="ontology.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col4:
        if st.button("🗑️ 清空图谱", use_container_width=True):
            st.session_state.knowledge_graph = {'nodes': [], 'edges': [], 'rules': []}
            save_current_project()
            st.success("✅ 图谱已清空")
            st.rerun()
    
    st.markdown("---")
    
    # 统计信息
    kg = st.session_state.knowledge_graph
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(render_stat_box("实体节点", len(kg.get('nodes', [])), "blue"), unsafe_allow_html=True)
    with col2:
        st.markdown(render_stat_box("关系边", len(kg.get('edges', [])), "green"), unsafe_allow_html=True)
    with col3:
        st.markdown(render_stat_box("规则数", len(kg.get('rules', [])), "orange"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 主要内容区
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.markdown("### ➕ 快速添加")
        
        # 添加节点
        with st.form("quick_add_node"):
            st.markdown("**添加节点**")
            node_name = st.text_input("节点名称", key="quick_node_name")
            node_type = st.selectbox("类型", ["实体", "属性", "概念", "约束"], key="quick_node_type")
            if st.form_submit_button("添加节点", use_container_width=True):
                if node_name.strip():
                    success, msg = add_node(node_name.strip(), node_type)
                    if success:
                        st.success("✅ 添加成功")
                        st.rerun()
                    else:
                        st.error(msg)
        
        # 添加关系
        nodes = kg.get('nodes', [])
        if len(nodes) >= 2:
            with st.form("quick_add_edge"):
                st.markdown("**添加关系**")
                node_names = [n.get('id') for n in nodes]
                source = st.selectbox("从", node_names, key="quick_source")
                relation = st.text_input("关系", key="quick_relation")
                target = st.selectbox("到", node_names, key="quick_target")
                if st.form_submit_button("添加关系", use_container_width=True):
                    if source and target and relation.strip() and source != target:
                        add_edge(source, target, relation.strip())
                        st.success("✅ 添加成功")
                        st.rerun()
    
    with col_right:
        # 显示可视化图谱
        show_knowledge_graph_visualization()
        
        # 如果没有安装 pyvis，显示替代的文本可视化
        if not PYVIS_AVAILABLE:
            st.markdown("### 🗺️ 文本可视化（pyvis未安装）")
            
            if kg.get('nodes'):
                st.markdown("**节点:**")
                node_html = ""
                for node in kg['nodes']:
                    node_html += f"<span style='display:inline-block;background:#e3f2fd;border:2px solid #2196f3;border-radius:20px;padding:5px 15px;margin:5px;'>{node.get('label')} ({node.get('type', '实体')})</span>"
                st.markdown(node_html, unsafe_allow_html=True)
                
                if kg.get('edges'):
                    st.markdown("**关系:**")
                    for edge in kg['edges']:
                        st.markdown(f"🔗 **{edge.get('source')}** --[{edge.get('relation')}]--> **{edge.get('target')}**")
                
                if kg.get('rules'):
                    st.markdown("**规则:**")
                    for rule in kg['rules']:
                        with st.expander(f"📜 {rule.get('name')}"):
                            st.write(rule.get('content'))
            else:
                st.info("📭 暂无节点数据，请通过左侧面板或本体管理添加节点")
                
                # 快速创建示例
                if st.button("🚀 创建示例图谱", type="primary"):
                    add_node("建筑高度", "属性")
                    add_node("高层建筑", "概念")
                    add_node("27米", "约束")
                    add_edge("高层建筑", "建筑高度", "具有属性")
                    add_edge("建筑高度", "27米", "大于")
                    add_rule("高层建筑判定", "IF 建筑高度 > 27m THEN 属于 高层建筑", "约束规则")
                    st.success("✅ 示例图谱已创建")
                    st.rerun()

# ==================== 主页面 ====================
def show_main_page():
    """显示主页面"""
    # 顶部操作栏
    st.markdown("### 📋 条文操作")
    ac1, ac2, ac3, ac4 = st.columns(4)
    
    with ac1:
        if st.button("🗑️ 删除条文", use_container_width=True):
            st.toast("请在表格中选择要删除的行", icon="ℹ️")
        if st.button("🔢 修改序号", use_container_width=True):
            st.toast("功能开发中", icon="🔧")
    
    with ac2:
        if st.button("➕ 插入条文", use_container_width=True):
            # 在末尾添加空行
            new_row = pd.DataFrame([{
                "规范": "",
                "条文": "",
                "条文内容": "",
                "实体标注": False,
                "关系标注": False,
                "规则标注": False
            }])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            save_current_project()
            st.success("✅ 已添加新行")
            st.rerun()
        if st.button("✂️ 拆解条文", use_container_width=True, disabled=True):
            pass
    
    with ac3:
        if st.button("🕸️ 图谱建模", type="primary", use_container_width=True):
            st.session_state.current_view = 'graph_modeling'
            st.rerun()
        if st.button("🔄 重新建模", use_container_width=True, disabled=True):
            pass
    
    with ac4:
        if st.button("🏷️ 标注规则", type="primary", use_container_width=True, disabled=True):
            pass
        if st.button("📝 重写规则", use_container_width=True, disabled=True):
            pass
    
    # 搜索筛选
    filtered_df = show_search_filter()
    if filtered_df is None:
        filtered_df = st.session_state.df
    
    # 批量操作
    show_batch_operations()
    
    st.markdown("---")
    
    # 数据表格
    display_df = filtered_df if filtered_df is not None else st.session_state.df
    
    if display_df.empty:
        st.info("ostringstream 暂无数据，请通过侧边栏 **导入规范** 添加数据")
        
        st.markdown("### 💡 快速开始")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **📥 导入数据**
            1. 点击左侧 **导入规范** 按钮
            2. 上传您的 CSV 或 Excel 文件
            3. 系统自动识别列并映射
            """)
        
        with col2:
            st.markdown("""
            **✅ 支持的格式**
            - CSV 文件 (.csv)
            - Excel 文件 (.xlsx, .xls)
            - 任意列名，自动识别
            """)
        
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
        
    else:
        # 显示筛选结果信息
        if len(display_df) != len(st.session_state.df):
            st.info(f"🔍 显示 {len(display_df)} / {len(st.session_state.df)} 条数据")
        
        column_config = {
            "规范": st.column_config.TextColumn("规范名称", width="medium"),
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
            num_rows="dynamic",
            key='main_data_editor'
        )
        
        # 检测变化并保存
        if not edited_df.equals(display_df):
            # 如果是筛选后的数据，需要更新原数据
            if len(display_df) != len(st.session_state.df):
                # 更新筛选后修改的数据
                for idx in edited_df.index:
                    if idx in st.session_state.df.index:
                        st.session_state.df.loc[idx] = edited_df.loc[idx]
            else:
                st.session_state.df = edited_df
            save_current_project()
    
    # 底部状态栏
    st.markdown("---")
    
    # 状态信息
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.session_state.current_project:
            st.caption(f"📂 **{st.session_state.current_project}**")
        else:
            st.caption("⚠️ 未选择项目")
    
    with col2:
        st.caption(f"📊 {len(st.session_state.df)} 条数据")
    
    with col3:
        if not st.session_state.df.empty:
            entity_done = st.session_state.df['实体标注'].sum() if '实体标注' in st.session_state.df.columns else 0
            relation_done = st.session_state.df['关系标注'].sum() if '关系标注' in st.session_state.df.columns else 0
            rule_done = st.session_state.df['规则标注'].sum() if '规则标注' in st.session_state.df.columns else 0
            total = len(st.session_state.df) * 3
            done = entity_done + relation_done + rule_done
            pct = int(done / total * 100) if total > 0 else 0
            st.caption(f"📈 标注进度: {pct}%")
        else:
            st.caption("📈 标注进度: 0%")
    
    with col4:
        st.caption("✅ 系统就绪")

# ==================== 侧边栏 ====================
def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        # Logo和标题
        st.markdown("""
            <div style="text-align: center; padding: 10px 0;">
                <h2>🏗️ 规范标注工具</h2>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 项目管理
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
        
        # 当前项目状态
        if st.session_state.current_project:
            st.success(f"**当前:** {st.session_state.current_project}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 保存", use_container_width=True):
                    save_current_project()
                    st.toast("✅ 项目已保存", icon="💾")
            with col2:
                if st.button("📤 导出", use_container_width=True):
                    export_project()
        else:
            st.warning("⚠️ 未选择项目")
            st.caption("请新建或打开一个项目开始工作")
        
        st.markdown("---")
        
        # 文件操作
        st.header("📄 文件操作")
        
        if st.button("📥 导入规范", type="primary", use_container_width=True):
            st.session_state.show_import_modal = True
            st.rerun()
        
        if st.button("🧠 本体管理", use_container_width=True):
            st.session_state.show_ontology_modal = True
            st.rerun()
        
        st.markdown("---")
        
        # 统计信息
        st.header("📈 统计信息")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📊 数据", len(st.session_state.df))
        with col2:
            st.metric("📁 项目", len(st.session_state.projects))
        
        # 本体统计
        kg = st.session_state.knowledge_graph
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🔹 节点", len(kg.get('nodes', [])))
        with col2:
            st.metric("🔗 关系", len(kg.get('edges', [])))
        
        # 标注进度
        if not st.session_state.df.empty:
            st.markdown("---")
            st.markdown("**📊 标注进度**")
            
            total = len(st.session_state.df)
            
            # 实体
            entity_done = int(st.session_state.df['实体标注'].sum()) if '实体标注' in st.session_state.df.columns else 0
            entity_pct = entity_done / total if total > 0 else 0
            st.progress(entity_pct, text=f"实体: {entity_done}/{total}")
            
            # 关系
            relation_done = int(st.session_state.df['关系标注'].sum()) if '关系标注' in st.session_state.df.columns else 0
            relation_pct = relation_done / total if total > 0 else 0
            st.progress(relation_pct, text=f"关系: {relation_done}/{total}")
            
            # 规则
            rule_done = int(st.session_state.df['规则标注'].sum()) if '规则标注' in st.session_state.df.columns else 0
            rule_pct = rule_done / total if total > 0 else 0
            st.progress(rule_pct, text=f"规则: {rule_done}/{total}")
        
        st.markdown("---")
        
        # 快捷操作
        st.header("⚡ 快捷操作")
        
        if st.button("🕸️ 图谱建模", type="primary", use_container_width=True):
            st.session_state.current_view = 'graph_modeling'
            st.rerun()
        
        if st.button("🏠 返回主页", use_container_width=True):
            st.session_state.current_view = 'main'
            st.rerun()
        
        # 版本信息
        st.markdown("---")
        st.caption("v1.0.0 | 建筑规范知识图谱标注工具")
        st.caption("© 2024 All Rights Reserved")

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
    if st.session_state.current_view == 'main':
        st.title("建筑设计规范 - 知识图谱标注工具")
    
    # 页面路由
    if st.session_state.current_view == 'graph_modeling':
        show_graph_modeling()
    else:
        show_main_page()

# 运行主程序
if __name__ == "__main__":
    main()



