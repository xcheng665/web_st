import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Empty, Input, List, Row, Select, Space, Spin, Statistic, Tag, Typography, message } from 'antd'
import { DiffOutlined, SearchOutlined, SwapOutlined } from '@ant-design/icons'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

const { Title, Text, Paragraph } = Typography

export default function StandardComparison() {
  const [keyword, setKeyword] = useState('净高')
  const [selectedSpecs, setSelectedSpecs] = useState([])
  const [specifications, setSpecifications] = useState([])
  const [comparison, setComparison] = useState(null)
  const [readiness, setReadiness] = useState(null)
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const navigate = useNavigate()
  const compare = async (value = keyword, ids = selectedSpecs) => {
    const term = value.trim()
    if (term.length < 2) { message.warning('请输入至少 2 个字符'); return }
    setSearching(true)
    try {
      const response = await axios.get('/api/standards/compare', { params: { keyword: term, spec_ids: ids.join(',') } })
      setComparison(response.data)
    } catch (error) { message.error(error.response?.data?.error || '规范对比失败') }
    finally { setSearching(false) }
  }
  useEffect(() => {
    Promise.all([axios.get('/api/specifications'), axios.get('/api/standards/version-readiness')])
      .then(([specResponse, readinessResponse]) => { setSpecifications(specResponse.data); setReadiness(readinessResponse.data); return compare('净高', []) })
      .catch(() => message.error('加载规范对比数据失败'))
      .finally(() => setLoading(false))
  }, []) // Initial evidence card loads once; later searches are user-triggered.
  if (loading) return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>
  const summary = comparison?.summary || { specifications: 0, clauses: 0, numeric_values: [], modal_terms: [] }
  return <div>
    <div className="page-heading"><div><div className="page-kicker">VERSION & EVIDENCE</div><Title level={2} className="page-title"><DiffOutlined style={{ color: '#b56a35' }} /> 规范证据对比</Title><Text type="secondary">围绕一个主题对照多本规范的数值、强制词、适用语句与原始条文。</Text></div><Tag color="gold">原文证据优先</Tag></div>
    <Alert type="info" showIcon message="不是“自动裁决”，而是可验证的规范阅读" description="系统仅并列展示已导入的条文证据。不同规范之间是否适用、是否冲突，仍需结合项目条件、规范版本和专业审核判断。" style={{ marginBottom: 16, borderRadius: 16 }} />
    <Card className="soft-panel" style={{ marginBottom: 16 }}><Space wrap><Input value={keyword} allowClear onChange={event => setKeyword(event.target.value)} onPressEnter={() => compare()} prefix={<SearchOutlined />} placeholder="例如：住宅净高、防火分区、无障碍" style={{ width: 255 }} /><Select mode="multiple" allowClear value={selectedSpecs} onChange={setSelectedSpecs} placeholder="限定规范范围（可选）" options={specifications.map(spec => ({ value: spec.id, label: spec.code }))} style={{ minWidth: 245 }} /><Button type="primary" icon={<SwapOutlined />} loading={searching} onClick={() => compare()} className="primary-green">对比条文</Button></Space></Card>
    <Row gutter={[14, 14]} style={{ marginBottom: 16 }}><Col xs={24} sm={8}><Card className="metric-card" style={{ '--metric-color': '#1f6f6b' }}><Statistic title="命中规范" value={summary.specifications} suffix="本" /></Card></Col><Col xs={24} sm={8}><Card className="metric-card" style={{ '--metric-color': '#b56a35' }}><Statistic title="相关条文" value={summary.clauses} suffix="条" /></Card></Col><Col xs={24} sm={8}><Card className="metric-card" style={{ '--metric-color': '#356c9b' }}><Text type="secondary">数值与强制词</Text><div style={{ marginTop: 8 }}><Space wrap>{summary.numeric_values?.length ? summary.numeric_values.map(value => <Tag color="volcano" key={value}>{value}</Tag>) : <Text type="secondary">未识别数值</Text>}{summary.modal_terms?.map(value => <Tag color="geekblue" key={value}>{value}</Tag>)}</Space></div></Card></Col></Row>
    <Row gutter={[16, 16]}><Col xs={24} xl={16}><Card className="work-card" title={`条文对照${comparison ? ` · “${comparison.keyword}”` : ''}`} extra={<Text type="secondary">{comparison?.notice}</Text>}>{comparison?.records?.length ? <List dataSource={comparison.records} pagination={{ pageSize: 7, hideOnSinglePage: true }} renderItem={record => <List.Item><List.Item.Meta title={<Space wrap><Tag color="cyan">{record.specification}</Tag><Text strong>第 {record.clause_number} 条</Text>{record.modal_terms.map(term => <Tag color="gold" key={term}>{term}</Tag>)}</Space>} description={<div>{record.sentences.map((sentence, index) => <Paragraph key={index} className="evidence-snippet" style={{ margin: '7px 0', lineHeight: 1.7 }}>{sentence}</Paragraph>)}<Space wrap>{record.numeric_values.map(value => <Tag color="volcano" key={value}>{value}</Tag>)}<Button type="link" size="small" style={{ paddingLeft: 0 }} onClick={() => navigate(`/specifications/${record.spec_id}/articles`)}>查看规范原文</Button></Space></div>} /></List.Item>} /> : <Empty description="未在已选规范中找到相关条文。" image={Empty.PRESENTED_IMAGE_SIMPLE} />}</Card></Col><Col xs={24} xl={8}><Card className="work-card" title="版本时光机 · 数据就绪度"><Paragraph type="secondary">真正的版本差异需要同一规范的两个或以上年份版本。当前不会把不同规范误当成不同版本。</Paragraph>{readiness?.ready_groups?.length ? <List dataSource={readiness.ready_groups} renderItem={group => <List.Item><List.Item.Meta title={group.family} description={group.versions.map(version => version.code).join(' / ')} /></List.Item>} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚无同规范多版本数据" />}<Text type="secondary" style={{ display: 'block', marginTop: 12 }}>{readiness?.message}</Text></Card></Col></Row>
  </div>
}
