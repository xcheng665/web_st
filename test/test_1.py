import streamlit as st
import pandas as pd
import json
from io import StringIO
from pathlib import Path
import os
# ======================
# 会话状态初始化
# ======================

# 初始化项目相关状态
if 'current_project' not in st.session_state:
    st.session_state.current_project = None

if 'projects' not in st.session_state:
    # 示例项目数据结构
    st.session_state.projects = {
        "默认项目": {
            'df': pd.DataFrame({
                'id': [1, 2, 3],
                '规范': ['建筑规范', '电气规范', '消防规范'],
                '条文': ['1.1', '2.3', '4.5'],
                '条文内容': [
                    '建筑物应符合当地建筑法规要求，确保结构安全和使用功能。',
                    '电气设备安装应遵循国家电气安全标准，确保用电安全。',
                    '消防设施应定期检查维护，确保在紧急情况下正常工作。'
                ]
            }),
            'created_at': '2025-12-05'
        }
    }
    st.session_state.current_project = "默认项目"

# 初始化模态框状态
for modal in ['show_import_modal', 'show_delete_modal', 'show_add_modal', 
              'show_edit_modal', 'show_new_project_modal']:
    if modal not in st.session_state:
        st.session_state[modal] = False

# 初始化操作状态
if 'delete_id' not in st.session_state:
    st.session_state.delete_id = 1

# ======================
# 工具函数
# ======================

def get_current_df():
    """获取当前项目的DataFrame"""
    if st.session_state.current_project and st.session_state.current_project in st.session_state.projects:
        return st.session_state.projects[st.session_state.current_project]['df']
    return pd.DataFrame(columns=['id', '规范', '条文', '条文内容'])

def set_current_df(df):
    """设置当前项目的DataFrame"""
    if st.session_state.current_project:
        st.session_state.projects[st.session_state.current_project]['df'] = df.copy()

def render_modal_header(title):
    """渲染弹窗头部"""
    st.markdown(f"<h3 style='text-align: center;'>{title}</h3>", unsafe_allow_html=True)
    st.markdown("---")

def render_modal_footer():
    """渲染弹窗底部"""
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray;'>© 2023 条文管理系统</div>", unsafe_allow_html=True)

def delete_row(row_id):
    """删除指定ID的行"""
    df = get_current_df()
    df = df[df['id'] != row_id].reset_index(drop=True)
    df['id'] = range(1, len(df) + 1)
    set_current_df(df)

def create_new_project(project_name):
    """创建新项目"""
    if project_name in st.session_state.projects:
        return False, f"项目 '{project_name}' 已存在"
    
    st.session_state.projects[project_name] = {
        'df': pd.DataFrame(columns=['id', '规范', '条文', '条文内容']),
        'created_at': pd.Timestamp.now().strftime('%Y-%m-%d')
    }
    st.session_state.current_project = project_name
    return True, f"项目 '{project_name}' 创建成功"

# ======================
# 导入功能
# ======================

def import_from_csv(file):
    """从CSV文件导入数据"""
    try:
        string_data = StringIO(file.getvalue().decode("utf-8"))
        df = pd.read_csv(string_data)
        
        required_columns = ['规范', '条文', '条文内容']
        if all(col in df.columns for col in required_columns):
            df['id'] = range(1, len(df) + 1)
            set_current_df(df[['id', '规范', '条文', '条文内容']])
            return True
        else:
            st.error("CSV文件缺少必需列: '规范', '条文', '条文内容'")
            return False
    except Exception as e:
        st.error(f"导入CSV文件时出错: {str(e)}")
        return False

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
        
        required_columns = ['规范', '条文', '条文内容']
        if all(col in df.columns for col in required_columns):
            df['id'] = range(1, len(df) + 1)
            set_current_df(df[['id', '规范', '条文', '条文内容']])
            return True
        else:
            st.error("JSON数据缺少必需字段: '规范', '条文', '条文内容'")
            return False
    except Exception as e:
        st.error(f"导入JSON文件时出错: {str(e)}")
        return False

def import_ontology(file):
    """导入本体文件（简化版）"""
    try:
        content = file.getvalue().decode("utf-8")
        sample_data = {
            '规范': [f'本体规范 - {file.name}'],
            '条文': ['1.0'],
            '条文内容': [f'从本体文件 {file.name} 中提取的规范内容示例']
        }
        df = pd.DataFrame(sample_data)
        df['id'] = range(1, len(df) + 1)
        set_current_df(df[['id', '规范', '条文', '条文内容']])
        return True
    except Exception as e:
        st.error(f"导入本体文件时出错: {str(e)}")
        return False

# ======================
# 模态框组件
# ======================

def show_new_project_modal():
    """新建项目弹窗"""
    if not st.session_state.show_new_project_modal:
        return
    
    with st.container():
        render_modal_header("📁 新建项目")
        
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

def show_import_modal():
    """导入规范弹窗"""
    if not st.session_state.get('show_import_modal', False):
        return
    
    with st.container():
        render_modal_header("📥 导入规范")
        
        st.markdown("**选择导入方式:**")
        
        import_option = st.radio(
            "导入类型",
            ("CSV文件", "JSON文件", "本体文件"),
            key="import_type"
        )
        
        uploaded_file = st.file_uploader(
            f"上传{import_option}",
            type=['csv'] if import_option == "CSV文件" 
                 else ['json'] if import_option == "JSON文件" 
                 else ['rdf', 'ttl', 'n3', 'owl'],
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
            st.info("JSON应包含数组，每项含规范、条文、条文内容字段")
        elif import_option == "本体文件":
            st.info("支持RDF/XML, Turtle(.ttl), N3, OWL等格式")
        
        render_modal_footer()

def show_delete_modal():
    """删除条文弹窗"""
    if not st.session_state.show_delete_modal:
        return
    
    with st.container():
        df = get_current_df()
        render_modal_header("🗑️ 删除条文")
        
        if df.empty:
            st.warning("⚠️ 当前没有可删除的条文")
            if st.button("关闭", key="close_empty_delete", type="secondary"):
                st.session_state.show_delete_modal = False
                st.rerun()
        else:
            st.markdown("**请选择要删除的条文ID:**")
            max_id = len(df)
            if st.session_state.delete_id > max_id:
                st.session_state.delete_id = max_id
                
            st.session_state.delete_id = st.slider(
                "拖动选择条文ID",
                min_value=1,
                max_value=max_id,
                value=st.session_state.delete_id,
                key="delete_slider"
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
                    st.text_area("条文内容预览", value=content_preview, height=100, disabled=True)
                
                st.warning("⚠️ 此操作不可撤销!")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ 确认删除", type="primary", use_container_width=True):
                        delete_row(st.session_state.delete_id)
                        st.session_state.show_delete_modal = False
                        st.success(f"✅ 已删除ID为 {st.session_state.delete_id} 的条文")
                        st.rerun()
                with col2:
                    if st.button("取消", type="secondary", use_container_width=True):
                        st.session_state.show_delete_modal = False
                        st.rerun()
            else:
                st.error("❌ 未找到该ID对应的条文")
                if st.button("关闭", type="secondary"):
                    st.session_state.show_delete_modal = False
                    st.rerun()
        
        render_modal_footer()

# ======================
# 主界面
# ======================
def init_project(project_name):
    project_dir = Path("projects") / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "clauses.csv").touch()
    (project_dir / "ontology.json").write_text(json.dumps({"entities": [], "relations": []}, indent=2))
    (project_dir / "annotations.json").write_text(json.dumps([], indent=2))
    return project_dir

def load_csv(file_path):
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return pd.read_csv(file_path)
    else:
        return pd.DataFrame(columns=["id", "clause_text"])

def save_csv(df, file_path):
    df.to_csv(file_path, index=False)

def load_ontology(onto_path):
    if os.path.exists(onto_path):
        with open(onto_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"entities": [], "relations": []}

def save_ontology(onto, onto_path):
    with open(onto_path, 'w', encoding='utf-8') as f:
        json.dump(onto, f, ensure_ascii=False, indent=2)

# ======================
# Streamlit App
# ======================

st.set_page_config(page_title="规范条文标注系统", layout="wide")
st.title("📜 规范条文标注系统")

# 侧边栏：项目管理
st.sidebar.header("📂 项目管理")
project_action = st.sidebar.radio("操作", ["新建项目", "打开现有项目"])

if project_action == "新建项目":
    new_proj_name = st.sidebar.text_input("新项目名称")
    if st.sidebar.button("创建项目"):
        if new_proj_name.strip():
            proj_dir = init_project(new_proj_name)
            st.session_state['current_project'] = str(proj_dir)
            st.sidebar.success(f"项目 '{new_proj_name}' 创建成功！")
        else:
            st.sidebar.error("项目名不能为空！")
elif project_action == "打开现有项目":
    projects = [d for d in Path("projects").iterdir() if d.is_dir()] if Path("projects").exists() else []
    if projects:
        proj_names = [p.name for p in projects]
        selected = st.sidebar.selectbox("选择项目", proj_names)
        if st.sidebar.button("打开项目"):
            st.session_state['current_project'] = str(Path("projects") / selected)
    else:
        st.sidebar.warning("暂无项目")

# 主界面逻辑
if 'current_project' not in st.session_state:
    st.info("请在左侧创建或打开一个项目")
else:
    proj_dir = Path(st.session_state['current_project'])
    st.subheader(f"当前项目：{proj_dir.name}")

    # ======================
    # Tab: 文件操作
    # ======================
    tab1, tab2 = st.tabs(["📁 文件操作", "🧠 本体操作"])

    with tab1:
        st.markdown("### 📥 导入规范条文（CSV）")
        uploaded_file = st.file_uploader("上传 clauses.csv（含 id, clause_text 列）", type="csv")
        if uploaded_file is not None:
            df_import = pd.read_csv(uploaded_file)
            if 'id' in df_import.columns and 'clause_text' in df_import.columns:
                save_csv(df_import, proj_dir / "clauses.csv")
                st.success("✅ 条文导入成功！")
            else:
                st.error("❌ CSV 必须包含 'id' 和 'clause_text' 列")

        st.markdown("### ➕ 插入规范条文（手动添加）")
        with st.form("add_clause"):
            new_id = st.text_input("条文 ID")
            new_text = st.text_area("条文内容")
            submit = st.form_submit_button("添加条文")
            if submit and new_id and new_text:
                df = load_csv(proj_dir / "clauses.csv")
                if new_id in df['id'].values:
                    st.warning("⚠️ ID 已存在")
                else:
                    new_row = pd.DataFrame([{"id": new_id, "clause_text": new_text}])
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_csv(df, proj_dir / "clauses.csv")
                    st.success("✅ 条文已添加")

        st.markdown("### 📤 输出标注结果（JSON）")
        # 假设 annotations.json 是你后续标注的结果（此处仅为示例）
        if st.button("下载标注结果.json"):
            anno_path = proj_dir / "annotations.json"
            if anno_path.exists():
                with open(anno_path, "rb") as f:
                    st.download_button(
                        label="⬇️ 下载 annotations.json",
                        data=f,
                        file_name="annotations.json",
                        mime="application/json"
                    )
            else:
                st.warning("标注结果文件不存在，请先进行标注")

        # 预览当前条文
        st.markdown("### 👀 当前条文预览")
        df = load_csv(proj_dir / "clauses.csv")
        st.dataframe(df, use_container_width=True)

    # ======================
    # Tab: 本体操作
    # ======================
    with tab2:
        onto_path = proj_dir / "ontology.json"
        onto = load_ontology(onto_path)

        st.markdown("### 🔽 载入本体")
        uploaded_onto = st.file_uploader("上传 ontology.json", type="json")
        if uploaded_onto is not None:
            try:
                new_onto = json.load(uploaded_onto)
                save_ontology(new_onto, onto_path)
                st.success("✅ 本体载入成功！")
                onto = new_onto
            except Exception as e:
                st.error(f"❌ 无效 JSON：{e}")

        st.markdown("### ✏️ 更新本体（编辑 JSON）")
        onto_str = st.text_area("本体内容（JSON 格式）", value=json.dumps(onto, ensure_ascii=False, indent=2), height=300)
        if st.button("保存本体"):
            try:
                updated_onto = json.loads(onto_str)
                save_ontology(updated_onto, onto_path)
                st.success("✅ 本体已更新！")
            except json.JSONDecodeError:
                st.error("❌ JSON 格式错误")

        st.markdown("### 🛠️ 构建本体（简易方式）")
        st.caption("你可以在此处添加实体类型或关系（未来可扩展为图形化构建）")
        new_entity = st.text_input("新增实体类型（如：材料、构件、荷载）")
        if st.button("添加实体") and new_entity.strip():
            if new_entity not in onto["entities"]:
                onto["entities"].append(new_entity)
                save_ontology(onto, onto_path)
                st.success(f"✅ 实体 '{new_entity}' 已添加")
            else:
                st.warning("⚠️ 实体已存在")

        st.markdown("### 📖 当前本体预览")
        st.json(onto)
st.title("📚 条文管理系统")

# 侧边栏：项目与导入
with st.sidebar:
    # 项目选择/创建
    st.header("📁 项目管理")
    
    project_names = list(st.session_state.projects.keys())
    selected_project = st.selectbox(
        "选择项目",
        options=project_names,
        index=project_names.index(st.session_state.current_project) if st.session_state.current_project in project_names else 0,
        key="project_selector"
    )
    
    if selected_project != st.session_state.current_project:
        st.session_state.current_project = selected_project
        st.rerun()
    
    if st.button("🆕 新建项目", type="primary", use_container_width=True):
        st.session_state.show_new_project_modal = True
        # 关闭其他弹窗
        for modal in ['show_import_modal', 'show_delete_modal', 'show_add_modal', 'show_edit_modal']:
            st.session_state[modal] = False
    
    st.divider()
    
    # 导入模块
    st.header("📥 导入")
    if st.button("导入规范", type="primary", use_container_width=True):
        st.session_state.show_import_modal = True
        for modal in ['show_new_project_modal', 'show_delete_modal', 'show_add_modal', 'show_edit_modal']:
            st.session_state[modal] = False
    
    if st.button("导入本体", type="secondary", use_container_width=True):
        st.session_state.show_import_modal = True
        for modal in ['show_new_project_modal', 'show_delete_modal', 'show_add_modal', 'show_edit_modal']:
            st.session_state[modal] = False

# 显示当前项目信息
if st.session_state.current_project:
    st.subheader(f"当前项目：{st.session_state.current_project}")
    project_info = st.session_state.projects[st.session_state.current_project]
    st.caption(f"创建时间：{project_info['created_at']} | 条文数量：{len(project_info['df'])}")

# 显示当前数据
df = get_current_df()
if not df.empty:
    st.dataframe(df, use_container_width=True)
else:
    st.info("当前项目中没有条文数据")

# 条文操作按钮（简化版）
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("➕ 插入条文", type="primary"):
        st.info("插入条文功能待实现")
with col2:
    if st.button("✏️ 编辑条文"):
        st.info("编辑条文功能待实现")
with col3:
    if st.button("🗑️ 删除条文"):
        st.session_state.show_delete_modal = True
        st.rerun()

# 显示所有弹窗
show_new_project_modal()
show_import_modal()
show_delete_modal()

# 样式优化
st.markdown("""
<style>
    [data-testid=stSidebar] {
        background-color: #f8f9fa;
    }
    .stButton>button {
        margin: 4px 0;
    }
</style>
""", unsafe_allow_html=True)