import streamlit as st
import pandas as pd
import os
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
import json
import re

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
        /* 图谱建模页面样式 */
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
        .entity-node {
            background-color: #e3f2fd;
            border: 2px solid #2196f3;
            border-radius: 8px;
            padding: 10px;
            margin: 5px;
            cursor: pointer;
        }
        .relation-edge {
            color: #4caf50;
            font-weight: bold;
        }
        .rule-container {
            background-color: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 15px;
            margin: 10px 0;
        }
        /* 弹窗样式 */
        .modal {
            display: block;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.4);
        }
        .modal-content {
            background-color: #fefefe;
            margin: 15% auto;
            padding: 20px;
            border: 1px solid #888;
            border-radius: 8px;
            width: 80%;
            max-width: 600px;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .close-btn {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #aaa;
        }
        .close-btn:hover {
            color: #000;
        }
        .modal-buttons {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-top: 15px;
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

# 初始化会话状态
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'main'
if 'knowledge_graph' not in st.session_state:
    st.session_state.knowledge_graph = {
        'nodes': [],
        'edges': [],
        'rules': []
    }
if 'selected_row' not in st.session_state:
    st.session_state.selected_row = None
if 'show_delete_modal' not in st.session_state:
    st.session_state.show_delete_modal = False
if 'show_insert_modal' not in st.session_state:
    st.session_state.show_insert_modal = False
if 'show_edit_modal' not in st.session_state:
    st.session_state.show_edit_modal = False
if 'editing_row' not in st.session_state:
    st.session_state.editing_row = None
if 'delete_id' not in st.session_state:
    st.session_state.delete_id = 1

# 加载数据
df = load_data()

def extract_entities(text):
    """从文本中提取实体"""
    # 简单的实体提取规则，实际项目中可以使用NLP工具
    entities = []
    patterns = [
        r'([甲乙丙丁戊己庚辛壬癸][类级])',  # 类别
        r'(\d+米)',  # 距离
        r'(\d+层)',  # 层数
        r'([一二三四五六七八九十\d]+级)',  # 等级
        r'(\d+平方米)',  # 面积
        r'([防火防烟防盗防爆防雷防静电防潮防虫防鼠防尘防辐射防电磁防光防声防热防冻防湿防滑防撞防坠防淹防爆防毒防污防锈防蚀防老化防变质防挥发防泄漏防扩散防冲击防震动防辐射防电磁防光防声防热防冻防湿防滑防撞防坠防淹防爆防毒防污防锈防蚀防老化防变质防挥发防泄漏防扩散防冲击防震动]设施)',  # 设施
        r'([建筑厂房仓库住宅宿舍公寓办公楼商店医院学校工厂车间实验室车库停车库变电站配电室锅炉房燃气调压站水池水箱消防站消防泵房消防控制室消防通道消防疏散通道消防楼梯消防电梯消防通道口消防门消防窗消防井消防栓消防水池消防水箱消防泵消防控制设备消防报警设备消防灭火设备消防疏散指示设备消防应急照明设备消防防烟排烟设备消防防火门消防防火窗消防防火卷帘消防防火阀消防排烟阀消防防火分隔设施消防防火分区消防防火墙消防防火堤消防防火沟消防防火沙池消防防火毯消防防火服消防防火靴消防防火 gloves消防防火头盔消防防火眼镜消防防火面罩消防防火口罩消防防火耳塞消防防火鞋消防防火帽消防防火衣消防防火裤消防防火外套消防防火内衬消防防火拉链消防防火扣子消防防火绳索消防防火梯消防防火钩消防防火锤消防防火斧消防防火锯消防防火刀消防防火剪消防防火钳消防防火扳手消防防火螺丝刀消防防火锤子消防防火钉子消防防火螺丝消防防火螺母消防防火垫片消防防火胶带消防防火涂料消防防火漆消防防火板消防防火砖消防防火石消防防火泥消防防火沙消防防火土消防防火水消防防火泡沫消防防火干粉消防防火二氧化碳消防防火氮气消防防火氩气消防防火氦气消防防火氖气消防防火氪气消防防火氙气消防防火氡气]设施)',  # 建筑类型
        r'([安全疏散通道安全出口疏散楼梯疏散走道疏散指示标志疏散照明应急照明应急广播应急电话应急广播系统应急广播设备应急广播设施应急广播器材应急广播系统设备应急广播系统设施应急广播系统器材应急广播设备系统应急广播设备设施应急广播设备器材应急广播设施系统应急广播设施设备应急广播设施器材应急广播器材系统应急广播器材设备应急广播器材设施]设施)',  # 安全设施
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if match not in entities:
                entities.append(match)
    
    return entities

def extract_relations(entities, text):
    """从实体和文本中提取关系"""
    relations = []
    if len(entities) >= 2:
        for i in range(len(entities)):
            for j in range(i+1, len(entities)):
                # 简单的关系提取
                if text.find(entities[i]) != -1 and text.find(entities[j]) != -1:
                    relations.append({
                        'source': entities[i],
                        'target': entities[j],
                        'relation': '关联',
                        'description': f"{entities[i]} 与 {entities[j]} 相关联"
                    })
    return relations

def build_knowledge_graph():
    """构建知识图谱"""
    nodes = []
    edges = []
    rules = []
    
    # 从标注的条文中提取实体和关系
    labeled_df = df[df["实体标注"] == "√"]
    
    for idx, row in labeled_df.iterrows():
        # 提取实体
        entities = extract_entities(row['条文内容'])
        
        # 为每个实体创建节点
        for entity in entities:
            if entity not in nodes:
                nodes.append({
                    'id': len(nodes) + 1,
                    'label': entity,
                    'type': 'entity',
                    'properties': {'source': row['条文'], 'content': row['条文内容']}
                })
        
        # 提取关系
        relations = extract_relations(entities, row['条文内容'])
        
        # 创建边
        for rel in relations:
            source_id = next((node['id'] for node in nodes if node['label'] == rel['source']), None)
            target_id = next((node['id'] for node in nodes if node['label'] == rel['target']), None)
            
            if source_id and target_id:
                edge = {
                    'id': len(edges) + 1,
                    'source': source_id,
                    'target': target_id,
                    'label': rel['relation'],
                    'description': rel['description']
                }
                if edge not in edges:
                    edges.append(edge)
    
    # 构建规则
    for idx, row in labeled_df.iterrows():
        rules.append({
            'id': len(rules) + 1,
            'content': row['条文内容'],
            'source': row['条文'],
            'entities': extract_entities(row['条文内容'])
        })
    
    return {
        'nodes': nodes,
        'edges': edges,
        'rules': rules
    }

def delete_row(row_id):
    """删除指定行"""
    global df
    df = df[df['id'] != row_id].reset_index(drop=True)
    df['id'] = range(1, len(df) + 1)

def insert_row(new_row_data):
    """插入新行"""
    global df
    new_row = pd.DataFrame({
        'id': [len(df) + 1],
        '规范': [new_row_data['规范']],
        '条文': [new_row_data['条文']],
        '条文内容': [new_row_data['条文内容']],
        '实体标注': [''],
        '关系标注': [''],
        '规则标注': ['']
    })
    df = pd.concat([df, new_row], ignore_index=True)

def update_row(row_id, updated_data):
    """更新指定行"""
    global df
    idx = df[df['id'] == row_id].index[0]
    df.at[idx, '规范'] = updated_data['规范']
    df.at[idx, '条文'] = updated_data['条文']
    df.at[idx, '条文内容'] = updated_data['条文内容']

def show_graph_modeling():
    """显示图谱建模页面"""
    st.title("知识图谱建模")
    
    # 控制面板
    with st.container():
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("图谱构建")
            if st.button("从标注数据构建图谱", type="primary", use_container_width=True):
                st.session_state.knowledge_graph = build_knowledge_graph()
                st.success("知识图谱构建完成！")
        
        with col2:
            st.subheader("导出选项")
            if st.button("导出为JSON", use_container_width=True):
                if st.session_state.knowledge_graph['nodes']:
                    json_data = json.dumps(st.session_state.knowledge_graph, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="下载JSON文件",
                        data=json_data,
                        file_name="knowledge_graph.json",
                        mime="application/json"
                    )
                else:
                    st.warning("请先构建图谱")
        
        with col3:
            st.subheader("图谱操作")
            if st.button("清空图谱", use_container_width=True):
                st.session_state.knowledge_graph = {'nodes': [], 'edges': [], 'rules': []}
                st.success("图谱已清空")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 显示图谱统计
    kg = st.session_state.knowledge_graph
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("实体数量", len(kg['nodes']))
    with col_stats2:
        st.metric("关系数量", len(kg['edges']))
    with col_stats3:
        st.metric("规则数量", len(kg['rules']))
    
    # 图谱可视化
    if kg['nodes']:
        st.subheader("知识图谱可视化")
        
        # 创建NetworkX图
        G = nx.Graph()
        
        # 添加节点
        for node in kg['nodes']:
            G.add_node(node['id'], label=node['label'], type=node['type'])
        
        # 添加边
        for edge in kg['edges']:
            G.add_edge(edge['source'], edge['target'], label=edge['label'])
        
        # 创建Pyvis网络
        net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
        net.from_nx(G)
        
        # 保存并显示
        net.save_graph("knowledge_graph.html")
        try:
            HtmlFile = open("knowledge_graph.html", 'r', encoding='utf-8')
            source_code = HtmlFile.read()
            st.components.v1.html(source_code, height=600)
        except FileNotFoundError:
            st.warning("图谱尚未生成，请先构建图谱")
    
    # 实体管理
    st.subheader("实体管理")
    if kg['nodes']:
        entity_df = pd.DataFrame(kg['nodes'])
        st.dataframe(entity_df[['label', 'type', 'properties']], use_container_width=True)
    else:
        st.info("暂无实体数据，请先构建图谱")
    
    # 关系管理
    st.subheader("关系管理")
    if kg['edges']:
        edge_df = pd.DataFrame(kg['edges'])
        st.dataframe(edge_df[['source', 'target', 'label', 'description']], use_container_width=True)
    else:
        st.info("暂无关系数据，请先构建图谱")
    
    # 规则管理
    st.subheader("规则管理")
    if kg['rules']:
        for rule in kg['rules']:
            with st.container():
                st.markdown(f'<div class="rule-container">', unsafe_allow_html=True)
                st.write(f"**规则 {rule['id']}** (来源: {rule['source']})")
                st.write(rule['content'])
                st.write(f"涉及实体: {', '.join(rule['entities'])}")
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("暂无规则数据，请先构建图谱")
    
    # 返回主页面按钮
    if st.button("返回主页面"):
        st.session_state.current_view = 'main'

def show_main_page():
    """显示主页面"""
    global df
    
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
            if st.button("删除\n条文", use_container_width=True):
                st.session_state.show_delete_modal = True
            if st.button("修改\n序号", use_container_width=True):
                st.session_state.show_edit_modal = True
        
        with ac2:
            if st.button("插入\n条文", use_container_width=True):
                st.session_state.show_insert_modal = True
            st.button("拆解\n条文", use_container_width=True)
        
        with ac3:
            if st.button("图谱\n建模", type="primary", use_container_width=True, help="核心功能：生成知识图谱"):
                st.session_state.current_view = 'graph_modeling'
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

    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=800, # 增加高度以展示更多数据
        disabled=["id", "规范", "条文", "条文内容", "实体标注", "关系标注", "规则标注"],
        key='data_editor'
    )

    # --- 弹窗模态 ---
    # 删除条文弹窗
    if st.session_state.show_delete_modal:
        st.markdown("""
        <div class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>删除条文</h3>
                    <button class="close-btn" id="close-delete-modal">&times;</button>
                </div>
                <p>请选择要删除的条文ID：</p>
        """, unsafe_allow_html=True)
        
        # 使用滑动条选择ID，限制范围
        max_id = len(df) if len(df) > 0 else 1
        st.session_state.delete_id = st.slider(
            "条文ID", 
            min_value=1, 
            max_value=max_id, 
            value=st.session_state.delete_id,
            key="delete_slider"
        )
        
        st.write(f"当前选择ID: {st.session_state.delete_id}")
        
        # 显示要删除的条文内容
        selected_row = df[df['id'] == st.session_state.delete_id]
        if not selected_row.empty:
            selected_row = selected_row.iloc[0]
            st.info(f"规范: {selected_row['规范']}")
            st.info(f"条文号: {selected_row['条文']}")
            st.info(f"内容: {selected_row['条文内容'][:100]}...")
        
        st.markdown('<div class="modal-buttons">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("确认删除", type="primary", key="confirm_delete_btn"):
                delete_row(st.session_state.delete_id)
                st.session_state.show_delete_modal = False
                st.success(f"已删除ID为 {st.session_state.delete_id} 的条文")
                st.rerun()
        with col2:
            if st.button("取消", key="cancel_delete_btn"):
                st.session_state.show_delete_modal = False
                st.rerun()
        
        st.markdown("</div></div></div>", unsafe_allow_html=True)
    
    # 插入条文弹窗
    if st.session_state.show_insert_modal:
        st.markdown("""
        <div class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>插入条文</h3>
                    <button class="close-btn" id="close-insert-modal">&times;</button>
                </div>
                <p>请输入新的条文信息：</p>
        """, unsafe_allow_html=True)
        
        new_specification = st.text_input("规范名称", value="建筑设计防火规范")
        new_article = st.text_input("条文号", value="第1条")
        new_content = st.text_area("条文内容", height=100)
        
        st.markdown('<div class="modal-buttons">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("确认插入", type="primary", key="confirm_insert_btn"):
                if new_specification and new_article and new_content:
                    insert_row({
                        '规范': new_specification,
                        '条文': new_article,
                        '条文内容': new_content
                    })
                    st.session_state.show_insert_modal = False
                    st.success("条文已插入")
                    st.rerun()
                else:
                    st.error("请填写所有字段")
        with col2:
            if st.button("取消", key="cancel_insert_btn"):
                st.session_state.show_insert_modal = False
                st.rerun()
        
        st.markdown("</div></div></div>", unsafe_allow_html=True)
    
    # 修改条文弹窗
    if st.session_state.show_edit_modal:
        st.markdown("""
        <div class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>修改条文</h3>
                    <button class="close-btn" id="close-edit-modal">&times;</button>
                </div>
                <p>请选择要修改的条文ID：</p>
        """, unsafe_allow_html=True)
        
        edit_id = st.number_input(
            "条文ID", 
            min_value=1, 
            max_value=len(df) if len(df) > 0 else 1, 
            value=1,
            key="edit_id_input"
        )
        
        # 获取当前条文信息
        current_row = df[df['id'] == edit_id]
        if not current_row.empty:
            current_row = current_row.iloc[0]
            edit_specification = st.text_input("规范名称", value=current_row['规范'], key="edit_spec_input")
            edit_article = st.text_input("条文号", value=current_row['条文'], key="edit_article_input")
            edit_content = st.text_area("条文内容", value=current_row['条文内容'], height=100, key="edit_content_input")
        
        st.markdown('<div class="modal-buttons">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("确认修改", type="primary", key="confirm_edit_btn"):
                if not current_row.empty:
                    update_row(edit_id, {
                        '规范': edit_specification,
                        '条文': edit_article,
                        '条文内容': edit_content
                    })
                    st.session_state.show_edit_modal = False
                    st.success(f"已修改ID为 {edit_id} 的条文")
                    st.rerun()
                else:
                    st.error("找不到指定ID的条文")
        with col2:
            if st.button("取消", key="cancel_edit_btn"):
                st.session_state.show_edit_modal = False
                st.rerun()
        
        st.markdown("</div></div></div>", unsafe_allow_html=True)

    # --- 底部状态栏 ---
    st.caption(f"当前共加载 {len(display_df)} 条数据 | 系统状态: 就绪 | 数据来源: GB 50016-2014(2018年版) 建筑设计防火规范.csv")

# 主页面路由
if st.session_state.current_view == 'graph_modeling':
    show_graph_modeling()
else:
    show_main_page()