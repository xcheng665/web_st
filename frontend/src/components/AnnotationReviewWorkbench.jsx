import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Col, Empty, Input, List, Row, Segmented, Select, Space, Spin, Tag, Typography, message } from 'antd'
import { CheckOutlined, CloseOutlined, EditOutlined, FileDoneOutlined, SaveOutlined } from '@ant-design/icons'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

const { Title, Text, Paragraph } = Typography
const stateMeta = { pending: ['待审核', 'gold'], applied: ['已通过', 'green'], rejected: ['已拒绝', 'red'] }

export default function AnnotationReviewWorkbench() {
  const [annotations, setAnnotations] = useState([])
  const [specifications, setSpecifications] = useState([])
  const [status, setStatus] = useState('pending')
  const [specId, setSpecId] = useState()
  const [selected, setSelected] = useState(null)
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const navigate = useNavigate()
  const load = async () => {
    setLoading(true)
    try {
      const [annotationResponse, specResponse] = await Promise.all([axios.get('/api/annotations', { params: { status, spec_id: specId } }), axios.get('/api/specifications')])
      setAnnotations(annotationResponse.data); setSpecifications(specResponse.data)
      setSelected(previous => {
        const next = annotationResponse.data.find(item => item.id === previous?.id) || annotationResponse.data[0] || null
        setDraft(next ? JSON.stringify(next.payload, null, 2) : '')
        return next
      })
    } catch { message.error('加载审核标注失败') }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [status, specId])
  const choose = item => { setSelected(item); setDraft(JSON.stringify(item.payload, null, 2)) }
  const save = async () => {
    if (!selected) return
    try {
      const payload = JSON.parse(draft)
      setSaving(true)
      const response = await axios.put(`/api/annotations/${selected.id}`, { payload })
      setSelected(response.data); setAnnotations(list => list.map(item => item.id === response.data.id ? response.data : item))
      message.success('修改已保存，尚未入图')
    } catch (error) { message.error(error instanceof SyntaxError ? 'JSON 格式无效' : error.response?.data?.error || '保存失败') }
    finally { setSaving(false) }
  }
  const decide = async action => {
    if (!selected) return
    try {
      setSaving(true)
      const response = await axios.post(`/api/annotations/${selected.id}/${action}`)
      message.success(action === 'apply' ? `已入图：实体 ${response.data.saved_entities || 0}，关系 ${response.data.saved_relations || 0}` : '标注已拒绝并保留审计记录')
      await load()
    } catch (error) { message.error(error.response?.data?.error || '审核操作失败') }
    finally { setSaving(false) }
  }
  const counts = useMemo(() => annotations.reduce((result, item) => ({ ...result, [item.status]: (result[item.status] || 0) + 1 }), {}), [annotations])
  return <div>
    <div className="page-heading"><div><div className="page-kicker">HUMAN-IN-THE-LOOP</div><Title level={2} className="page-title"><FileDoneOutlined style={{ color: '#b56a35' }} /> 标注审核工作台</Title><Text type="secondary">编辑结构化抽取、置信度与连续原文证据后，再决定是否写入知识图谱。</Text></div><Space><Segmented value={status} onChange={setStatus} options={['pending', 'applied', 'rejected'].map(value => ({ value, label: stateMeta[value][0] }))} /><Select allowClear value={specId} onChange={setSpecId} placeholder="筛选规范" options={specifications.map(spec => ({ value: spec.id, label: spec.code }))} style={{ minWidth: 145 }} /></Space></div>
    <Alert type="info" showIcon message="审核规则" description="只允许修改待审核标注；原始条文始终显示在右侧作为证据锚点。已通过和已拒绝的记录不可静默改写。" style={{ marginBottom: 16, borderRadius: 16 }} />
    <Row gutter={16}><Col xs={24} lg={9}><Card className="work-card" title={`${stateMeta[status][0]} · ${annotations.length} 条`} extra={<Tag color={stateMeta[status][1]}>{counts[status] || 0}</Tag>}><List loading={loading} dataSource={annotations} locale={{ emptyText: '当前筛选条件下没有标注' }} renderItem={item => <List.Item className={`review-list-item ${selected?.id === item.id ? 'is-selected' : ''}`} onClick={() => choose(item)}><List.Item.Meta title={<Space wrap><Tag color={stateMeta[item.status][1]}>{stateMeta[item.status][0]}</Tag><Text strong>#{item.id}</Text><Text type="secondary">{item.article?.specification} · {item.article?.clause_number}</Text></Space>} description={`${item.payload.entities?.length || 0} 实体 · ${item.payload.relations?.length || 0} 关系 · ${item.model || '本地模型'}`} /></List.Item>} /></Card></Col><Col xs={24} lg={15}><Card className="work-card" title="审核与证据"><Spin spinning={loading}>{selected ? <><Space style={{ marginBottom: 12 }} wrap><Tag color={stateMeta[selected.status][1]}>{stateMeta[selected.status][0]}</Tag><Text>{selected.article?.specification} 第 {selected.article?.clause_number} 条</Text></Space><Paragraph className="evidence-snippet" style={{ whiteSpace: 'pre-wrap' }}>{selected.article?.content}</Paragraph>{selected.status === 'pending' ? <><Text strong>结构化标注（可编辑）</Text><Input.TextArea className="code-editor" value={draft} onChange={event => setDraft(event.target.value)} autoSize={{ minRows: 14, maxRows: 24 }} /><Space style={{ marginTop: 12 }} wrap><Button icon={<SaveOutlined />} onClick={save} loading={saving}>保存修改</Button><Button type="primary" icon={<CheckOutlined />} onClick={() => decide('apply')} loading={saving} className="primary-green">通过并入图</Button><Button danger icon={<CloseOutlined />} onClick={() => decide('reject')} loading={saving}>拒绝</Button><Button type="link" onClick={() => navigate(`/specifications/${selected.article.spec_id}/articles`)}>查看上下文条文</Button></Space></> : <Empty description="该标注已完成审核，内容保持只读以保留审计轨迹。" image={Empty.PRESENTED_IMAGE_SIMPLE} />}</> : <Empty description="从左侧选择一条标注开始审核" />}</Spin></Card></Col></Row>
  </div>
}
