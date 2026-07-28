import { useEffect, useMemo, useRef, useState } from 'react'
import { Badge, Button, Card, Empty, Input, Progress, Select, Space, Tag, Typography, message } from 'antd'
import { DownloadOutlined, FilterOutlined, ShareAltOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import axios from 'axios'
import { DataSet, Network } from 'vis-network/standalone'
import { useNavigate } from 'react-router-dom'

const { Title, Text, Paragraph } = Typography
const colors = { '建筑对象': '#1f6f6b', '部位': '#3b82a0', '性能指标': '#bd7a35', '数值': '#9b5e4e', '标准': '#6a617b', '行为': '#508552', '实体': '#1f6f6b', '属性': '#bd7a35', '概念': '#3b82a0', '约束': '#9b5e4e', '其他': '#7a7a70' }

export default function KnowledgeGraph() {
  const [raw, setRaw] = useState({ nodes: [], edges: [] })
  const [loading, setLoading] = useState(true)
  const [keyword, setKeyword] = useState('')
  const [types, setTypes] = useState([])
  const [relations, setRelations] = useState([])
  const [specId, setSpecId] = useState()
  const [specs, setSpecs] = useState([])
  const [selected, setSelected] = useState(null)
  const navigate = useNavigate()
  const ref = useRef(null)
  const instance = useRef(null)

  const load = async () => {
    setLoading(true)
    try {
      setRaw((await axios.get('/api/knowledge_graph')).data)
      setSelected(null)
    } catch {
      message.error('获取知识模型失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    axios.get('/api/specifications').then(response => setSpecs(response.data))
  }, [])

  const typeOptions = useMemo(() => [...new Set(raw.nodes.map(node => node.entity_type))].map(type => ({ label: type, value: type })), [raw])
  const relationOptions = useMemo(() => [...new Set(raw.edges.map(edge => edge.relation_type))].map(type => ({ label: type, value: type })), [raw])
  const graph = useMemo(() => {
    const nodes = raw.nodes
      .filter(node => (!keyword || node.name.includes(keyword)) && (!types.length || types.includes(node.entity_type)) && (!specId || node.spec_ids?.includes(specId)))
      .map(node => ({
        ...node,
        id: String(node.id),
        label: node.name,
        color: { background: colors[node.entity_type] || colors.其他, border: '#fffdf7', highlight: { background: '#d7b56d', border: '#183a37' } },
        font: { color: '#fffdf7', face: 'Microsoft YaHei' },
        title: `${node.entity_type}｜${node.name}`,
      }))
    const ids = new Set(nodes.map(node => node.id))
    const edges = raw.edges
      .filter(edge => ids.has(String(edge.source_id)) && ids.has(String(edge.target_id)) && (!relations.length || relations.includes(edge.relation_type)) && (!specId || edge.spec_ids?.includes(specId)))
      .map(edge => ({
        ...edge,
        id: String(edge.id),
        from: String(edge.source_id),
        to: String(edge.target_id),
        label: edge.relation_type,
        font: { color: '#5e655b', size: 12, strokeWidth: 3, strokeColor: '#fffdf7', align: 'middle' },
        color: { color: '#9aa295', highlight: '#b56a35' },
        arrows: 'to',
      }))
    return { nodes, edges }
  }, [raw, keyword, types, relations, specId])

  useEffect(() => {
    if (!ref.current) return
    instance.current?.destroy()
    if (!graph.nodes.length) return
    instance.current = new Network(ref.current, { nodes: new DataSet(graph.nodes), edges: new DataSet(graph.edges) }, {
      nodes: { shape: 'dot', size: 23, borderWidth: 2, shadow: { enabled: true, color: 'rgba(24,58,55,.18)', size: 10 } },
      edges: { width: 1.6, smooth: { type: 'dynamic' } },
      physics: { stabilization: { iterations: 120 }, barnesHut: { gravitationalConstant: -3300, centralGravity: .16, springLength: 135, springConstant: .045, avoidOverlap: .6 } },
      interaction: { hover: true, navigationButtons: true, keyboard: true },
    })
    instance.current.on('click', params => {
      const node = graph.nodes.find(item => item.id === params.nodes[0])
      const edge = graph.edges.find(item => item.id === params.edges[0])
      setSelected(node ? { kind: 'node', value: node } : edge ? { kind: 'edge', value: edge } : null)
    })
    return () => instance.current?.destroy()
  }, [graph])

  const exportGraph = () => {
    const blob = new Blob([JSON.stringify(raw, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'building-code-knowledge-model.json'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return <div>
    <div className="page-heading">
      <div>
        <div className="page-kicker">GRAPH EXPLORER</div>
        <Title level={2} className="page-title"><ShareAltOutlined style={{ color: '#b56a35' }} /> 知识模型</Title>
        <Text type="secondary">左侧筛选，中间浏览图谱，右侧追溯条文证据；点击任意节点或关系即可查看详情。</Text>
      </div>
      <Space><Button icon={<ReloadOutlined />} onClick={load} loading={loading}>刷新</Button><Button type="primary" icon={<DownloadOutlined />} onClick={exportGraph} className="primary-green">导出 JSON</Button></Space>
    </div>

    <div className="graph-layout">
      <Card className="work-card" title={<><FilterOutlined /> 图谱筛选</>}>
        <div className="graph-filter-stack">
          <Input allowClear prefix={<SearchOutlined />} placeholder="查找实体名称" value={keyword} onChange={event => setKeyword(event.target.value)} />
          <Select allowClear placeholder="规范范围" value={specId} onChange={setSpecId} options={specs.map(spec => ({ value: spec.id, label: `${spec.code}` }))} />
          <Select mode="multiple" allowClear placeholder="实体类型" value={types} onChange={setTypes} options={typeOptions} />
          <Select mode="multiple" allowClear placeholder="关系类型" value={relations} onChange={setRelations} options={relationOptions} />
          <Card size="small" className="soft-panel">
            <Space direction="vertical" size={6}>
              <Badge color="#1f6f6b" text={`${graph.nodes.length} 个节点`} />
              <Badge color="#b56a35" text={`${graph.edges.length} 条关系`} />
              <Text type="secondary">筛选会同步裁剪节点和关系，避免孤立边干扰判断。</Text>
            </Space>
          </Card>
          <Button onClick={() => { setKeyword(''); setTypes([]); setRelations([]); setSpecId(undefined) }}>清空筛选</Button>
        </div>
      </Card>

      <Card className="graph-canvas-card">
        {loading ? <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}>正在装配知识网络…</div> : graph.nodes.length ? <div ref={ref} style={{ height: 620 }} /> : <Empty description="还没有已审核的知识节点。" style={{ marginTop: 190 }}>
          <Space><Button onClick={() => navigate('/settings')}>批量标注</Button><Button type="primary" onClick={() => navigate('/specifications')} className="primary-green">查看规范</Button></Space>
        </Empty>}
      </Card>

      <Card className="work-card evidence-card" title="证据与详情">
        {selected?.kind === 'node' ? <NodeEvidence selected={selected.value} /> : selected?.kind === 'edge' ? <EdgeEvidence selected={selected.value} /> : <div style={{ paddingTop: 150, textAlign: 'center' }}>
          <ShareAltOutlined style={{ fontSize: 34, color: '#c4b99f' }} />
          <Paragraph type="secondary" style={{ marginTop: 12 }}>选择节点或关系，查看其类型、证据强度、原文条文和审查状态。</Paragraph>
        </div>}
      </Card>
    </div>

    <Card size="small" title="图例" className="work-card" style={{ marginTop: 16 }}><Space wrap>{Object.entries(colors).map(([type, color]) => <Badge key={type} color={color} text={type} />)}</Space></Card>
  </div>
}

function NodeEvidence({ selected }) {
  return <>
    <Tag color="cyan">{selected.entity_type}</Tag>
    <Title level={4}>{selected.name}</Title>
    {selected.description && <Paragraph>{selected.description}</Paragraph>}
    <EvidenceStrength strength={selected.evidence_strength} />
    <Title level={5}>原文证据</Title>
    {selected.evidence?.length ? selected.evidence.map(item => <div className="evidence-snippet" key={item.article_id}>
      <Text strong>第 {item.clause_number} 条</Text>
      <Paragraph style={{ margin: '6px 0 0', lineHeight: 1.65 }}>{item.content}</Paragraph>
    </div>) : <Text type="secondary">该节点由旧数据创建，暂未保留条文关联。</Text>}
  </>
}

function EdgeEvidence({ selected }) {
  return <>
    <Tag color="gold">关系</Tag>
    <Title level={4}>{selected.source_name} → {selected.target_name}</Title>
    <Paragraph><Text strong>{selected.relation_type}</Text></Paragraph>
    <EvidenceStrength strength={selected.evidence_strength} />
    <Text type="secondary">证据：{selected.description || '未记录（旧数据）'}</Text>
  </>
}

function EvidenceStrength({ strength }) {
  if (!strength) return null
  return <Card size="small" className="soft-panel" style={{ margin: '10px 0' }}>
    <Text strong>证据强度</Text>
    <Progress percent={strength.score} size="small" strokeColor="#1f6f6b" format={value => `${value}/100`} />
    <Space wrap><Tag color={strength.reviewed ? 'green' : 'gold'}>{strength.status}</Tag><Text type="secondary">原文条文 {strength.article_count} 条</Text>{strength.llm_confidence !== null && <Text type="secondary">LLM 置信度 {Math.round(strength.llm_confidence * 100)}%</Text>}</Space>
  </Card>
}
