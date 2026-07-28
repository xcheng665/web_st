import { useEffect, useState } from 'react'
import { Alert, Badge, Button, Card, Descriptions, Input, Modal, Space, Table, Tag, Typography, message } from 'antd'
import { ArrowLeftOutlined, CopyOutlined, RobotOutlined, SearchOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import axios from 'axios'
import { useNavigate, useParams } from 'react-router-dom'

const { Title, Text, Paragraph } = Typography

function AnnotationPanel({ annotation, onApplied }) {
  if (!annotation) return null
  const data = annotation.payload
  const apply = async () => {
    try {
      const response = await axios.post(`/api/annotations/${annotation.id}/apply`)
      message.success(`已入图：${response.data.saved_entities} 个实体、${response.data.saved_relations} 条关系`)
      onApplied()
    } catch (error) { message.error(error.response?.data?.error || '写入图谱失败') }
  }
  return <div>
    <Alert type={annotation.status === 'applied' ? 'success' : 'info'} showIcon message={annotation.status === 'applied' ? '该结果已审核并写入知识图谱' : '请核对条文证据后确认入图'} style={{ marginBottom: 16 }} />
    <Descriptions size="small" column={2} bordered><Descriptions.Item label="模型">{annotation.model || '—'}</Descriptions.Item><Descriptions.Item label="状态">{annotation.status === 'applied' ? '已入图' : '待审核'}</Descriptions.Item></Descriptions>
    <Title level={5} style={{ marginTop: 18 }}>实体（{data.entities?.length || 0}）</Title>
    {(data.entities || []).map((item, index) => <Card key={`${item.name}-${index}`} size="small" style={{ marginBottom: 8 }}><Tag color="cyan">{item.type}</Tag><Text strong>{item.name}</Text><Text type="secondary"> · 置信度 {Math.round((item.confidence || 0) * 100)}%</Text><Paragraph type="secondary" style={{ margin: '6px 0 0' }}>证据：{item.evidence}</Paragraph></Card>)}
    <Title level={5} style={{ marginTop: 18 }}>关系（{data.relations?.length || 0}）</Title>
    {(data.relations || []).map((item, index) => <Card key={`${item.source}-${index}`} size="small" style={{ marginBottom: 8 }}><Text strong>{item.source}</Text> <Tag color="gold">{item.predicate}</Tag> <Text strong>{item.target}</Text><Paragraph type="secondary" style={{ margin: '6px 0 0' }}>证据：{item.evidence}</Paragraph></Card>)}
    <Title level={5} style={{ marginTop: 18 }}>规则（{data.rules?.length || 0}）</Title>
    {(data.rules || []).map((item, index) => <Card key={`${item.name}-${index}`} size="small" style={{ marginBottom: 8 }}><Tag color="volcano">{item.rule_type}</Tag><Text strong>{item.name}</Text><Paragraph style={{ margin: '6px 0 0' }}>{item.content}</Paragraph><Text type="secondary">证据：{item.evidence}</Text></Card>)}
    {annotation.status !== 'applied' && <Button type="primary" icon={<SafetyCertificateOutlined />} onClick={apply} style={{ marginTop: 18, background: '#b56a35' }}>审核通过并写入图谱</Button>}
  </div>
}

export default function ArticleList() {
  const { specId } = useParams(); const navigate = useNavigate()
  const [articles, setArticles] = useState([]); const [specification, setSpecification] = useState(null); const [loading, setLoading] = useState(true)
  const [searchText, setSearchText] = useState(''); const [modal, setModal] = useState({ open: false, loading: false, annotation: null, article: null }); const [llmReady, setLlmReady] = useState(null)
  const fetchArticles = async () => { setLoading(true); try { setArticles((await axios.get(`/api/specifications/${specId}/articles`)).data) } catch { message.error('获取条文列表失败') } finally { setLoading(false) } }
  useEffect(() => { fetchArticles(); axios.get(`/api/specifications/${specId}`).then(r => setSpecification(r.data)); axios.get('/api/llm/status').then(r => setLlmReady(r.data)).catch(() => setLlmReady({ configured: false })) }, [specId])
  const annotate = async (article) => { setModal({ open: true, loading: true, annotation: null, article }); try { const result = await axios.post(`/api/articles/${article.id}/llm-annotations`); setModal({ open: true, loading: false, annotation: result.data, article }) } catch (error) { message.error(error.response?.data?.error || 'LLM 标注失败'); setModal({ open: false, loading: false, annotation: null, article: null }) } }
  const viewLatest = async (article) => { try { const list = (await axios.get(`/api/articles/${article.id}/annotations`)).data; if (!list.length) return annotate(article); setModal({ open: true, loading: false, annotation: list[0], article }) } catch { message.error('读取标注失败') } }
  const filtered = articles.filter(a => a.clause_number.includes(searchText) || a.content.includes(searchText))
  const highlight = value => { if (!searchText) return value; const parts = value.split(searchText); return <>{parts.map((part, index) => <span key={index}>{part}{index < parts.length - 1 && <mark>{searchText}</mark>}</span>)}</> }
  const columns = [
    { title: '条文号', dataIndex: 'clause_number', width: 110, render: value => <Tag color="geekblue">{value}</Tag> },
    { title: '条文内容', dataIndex: 'content', render: value => <div style={{ maxWidth: 600, lineHeight: 1.7 }}>{highlight(value)}</div> },
    { title: '标注状态', width: 105, render: (_, row) => row.entity_tagged || row.relation_tagged || row.rule_tagged ? <Badge status="success" text="已入图" /> : <Badge status="default" text="未标注" /> },
    { title: '操作', width: 250, render: (_, row) => <Space><Button type="primary" size="small" icon={<RobotOutlined />} onClick={() => annotate(row)} disabled={!llmReady?.configured}>LLM 标注</Button><Button size="small" onClick={() => viewLatest(row)}>查看结果</Button><Button size="small" icon={<CopyOutlined />} onClick={() => navigator.clipboard.writeText(row.content).then(() => message.success('条文已复制'))}>复制</Button></Space> }
  ]
  return <div>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}><div><Button size="small" icon={<ArrowLeftOutlined />} onClick={() => navigate('/specifications')} style={{ marginBottom: 12 }}>返回规范库</Button><Title level={2} style={{ margin: 0 }}>{specification ? `${specification.code} · 条文标注` : '条文标注'}</Title><Text type="secondary">以条文原文为证据，使用 LLM 抽取实体、关系与可验证规则。</Text></div><Input placeholder="检索条文" prefix={<SearchOutlined />} value={searchText} onChange={e => setSearchText(e.target.value)} style={{ width: 260 }} /></div>
    {llmReady && !llmReady.configured && <Alert type="warning" showIcon message="LLM API 尚未配置" description="复制 backend/.env.example 为 backend/.env，填入 LLM_API_KEY 后重启后端服务，即可调用自动标注。" style={{ marginBottom: 16 }} />}
    <Card title={`共 ${filtered.length} 条条文`}><Table columns={columns} dataSource={filtered} rowKey="id" loading={loading} pagination={{ pageSize: 8 }} scroll={{ x: 900 }} expandable={{expandedRowRender: row => <div style={{lineHeight:1.8, padding:'4px 14px'}}>{highlight(row.content)}</div>, rowExpandable: () => true}} /></Card>
    <Modal title={modal.article ? `LLM 标注 · 第 ${modal.article.clause_number} 条` : 'LLM 标注'} open={modal.open} onCancel={() => setModal({ ...modal, open: false })} footer={null} width={820} destroyOnClose>{modal.loading ? <div style={{ padding: 48, textAlign: 'center' }}><RobotOutlined spin style={{ fontSize: 32, color: '#b56a35' }} /><Paragraph style={{ marginTop: 16 }}>正在读取条文并调用模型抽取知识…</Paragraph></div> : <AnnotationPanel annotation={modal.annotation} onApplied={() => { fetchArticles(); setModal({ ...modal, annotation: { ...modal.annotation, status: 'applied' } }) }} />}</Modal>
  </div>
}
