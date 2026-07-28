import { useCallback, useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Col, Descriptions, Divider, Empty, Form, Input, InputNumber, List, Row, Select, Space, Spin, Statistic, Switch, Tag, Typography, message } from 'antd'
import { CheckCircleOutlined, FileSearchOutlined, PlusOutlined, SafetyCertificateOutlined, WarningOutlined } from '@ant-design/icons'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

const { Title, Text, Paragraph } = Typography
const statusMeta = {
  pass: { label: '通过', color: 'green', icon: <CheckCircleOutlined /> },
  fail: { label: '不满足', color: 'red', icon: <WarningOutlined /> },
  pending: { label: '待确认', color: 'gold', icon: <FileSearchOutlined /> },
  advisory: { label: '提示', color: 'blue', icon: <SafetyCertificateOutlined /> },
}

function FieldControl({ field }) {
  if (field.type === 'select') return <Select allowClear options={field.options.map(value => ({ value, label: field.unit ? `${value}${field.unit}` : value }))} />
  if (field.type === 'boolean') return <Switch checkedChildren="是" unCheckedChildren="否" />
  if (field.type === 'number') return <InputNumber min={0} precision={field.unit === 'm' ? 2 : 0} style={{ width: '100%' }} addonAfter={field.unit} />
  return <Input allowClear placeholder={`填写${field.label}`} />
}

function ResultItem({ item }) {
  const meta = statusMeta[item.status] || statusMeta.pending
  const navigate = useNavigate()
  const evidence = item.article
  return <List.Item style={{ alignItems: 'flex-start' }}>
    <List.Item.Meta
      title={<Space wrap><Tag color={meta.color} icon={meta.icon}>{meta.label}</Tag><Text strong>{item.title}</Text><Text type="secondary">{item.category}</Text></Space>}
      description={<div><div style={{ marginTop: 6 }}>{item.explanation}</div><div style={{ color: '#695f4e', marginTop: 6 }}>项目值：{item.input_value ?? '未填写'}　要求：{item.expected_value}</div>{evidence ? <Card size="small" style={{ marginTop: 10, background: '#faf5e9', borderColor: '#e8dbc2' }}><Space direction="vertical" size={4}><Text strong>{evidence.specification} · {evidence.clause_number}</Text><Paragraph ellipsis={{ rows: 2, expandable: true, symbol: '展开原文' }} style={{ marginBottom: 0 }}>{evidence.content}</Paragraph><Button type="link" size="small" style={{ paddingLeft: 0 }} onClick={() => navigate(`/specifications/${evidence.spec_id}/articles`)}>查看所在规范条文</Button></Space></Card> : <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>暂未定位可直接判定的完整条文证据。</Text>}</div>}
    />
  </List.Item>
}

export default function ComplianceWorkbench() {
  const [form] = Form.useForm()
  const [schema, setSchema] = useState([])
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState(null)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [creating, setCreating] = useState(false)

  const groups = useMemo(() => schema.reduce((acc, field) => { (acc[field.group] ||= []).push(field); return acc }, {}), [schema])
  const load = useCallback(async () => {
    try {
      const [schemaResponse, projectResponse] = await Promise.all([axios.get('/api/compliance/schema'), axios.get('/api/projects')])
      setSchema(schemaResponse.data.fields || [])
      setProjects(projectResponse.data || [])
      const first = projectResponse.data?.[0]
      if (first) {
        setSelectedProject(first)
        form.setFieldsValue({ project_name: first.name, ...first.parameters })
        const reportResponse = await axios.get(`/api/projects/${first.id}/compliance-report`)
        if (reportResponse.data.results?.length) setReport(reportResponse.data)
      }
    } catch { message.error('加载合规体检数据失败') }
    finally { setLoading(false) }
  }, [form])
  useEffect(() => { load() }, [load])

  const selectProject = async (id) => {
    const project = projects.find(item => item.id === id)
    if (!project) return
    setCreating(false); setSelectedProject(project); setReport(null)
    form.setFieldsValue({ project_name: project.name, ...project.parameters })
    try { const response = await axios.get(`/api/projects/${id}/compliance-report`); if (response.data.results?.length) setReport(response.data) } catch { message.error('读取项目报告失败') }
  }
  const newProject = () => {
    setCreating(true); setSelectedProject(null); setReport(null)
    form.resetFields(); form.setFieldValue('occupancy', '住宅')
  }
  const saveAndCheck = async (values) => {
    const { project_name: name, ...parameters } = values
    if (!name?.trim()) { message.warning('请填写项目名称'); return }
    setRunning(true)
    try {
      let project = selectedProject
      if (project && !creating) {
        const response = await axios.put(`/api/projects/${project.id}`, { name, parameters }); project = response.data
      } else {
        const response = await axios.post('/api/projects', { name, parameters }); project = response.data
      }
      const response = await axios.post(`/api/projects/${project.id}/compliance-check`, { parameters })
      setSelectedProject(response.data.project); setReport(response.data); setCreating(false)
      setProjects(previous => [response.data.project, ...previous.filter(item => item.id !== response.data.project.id)])
      message.success('体检已完成：每条结论均保留原文证据或待确认原因')
    } catch (error) { message.error(error.response?.data?.error || '体检执行失败') }
    finally { setRunning(false) }
  }
  if (loading) return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>
  const summary = report?.summary || { pass: 0, fail: 0, pending: 0, advisory: 0 }
  return <div>
    <div className="page-heading"><div><div className="page-kicker">COMPLIANCE CHECK</div><Title level={2} className="page-title" style={{ fontFamily: 'STKaiti, KaiTi, serif' }}>设计方案合规体检</Title><Text type="secondary">从项目条件定位条文，再输出可验证、可审计的方案阶段结论。</Text></div><Space><Select value={selectedProject?.id} placeholder="选择项目档案" style={{ minWidth: 190 }} options={projects.map(item => ({ value: item.id, label: item.name }))} onChange={selectProject} /><Button icon={<PlusOutlined />} onClick={newProject}>新建项目</Button></Space></div>
    <Alert showIcon type="info" message="证据优先的判定边界" description="“通过 / 不满足”仅用于已匹配到明确、可计算的条文；缺少适用条件、版本或原始数据时，系统会保留为“待确认”，而不是生成不可靠的结论。" style={{ marginBottom: 18, borderRadius: 16 }} />
    <Row gutter={[18, 18]}>
      <Col xs={24} xl={9}><Card className="work-card" title="01 · 项目条件" extra={<Tag color="geekblue">可保存复用</Tag>}><Form form={form} layout="vertical" onFinish={saveAndCheck} initialValues={{ occupancy: '住宅' }}><Form.Item name="project_name" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]}><Input placeholder="例如：滨江社区住宅一期" /></Form.Item>{Object.entries(groups).map(([group, fields]) => <div key={group}><Divider orientation="left" plain>{group}</Divider><Row gutter={12}>{fields.map(field => <Col span={field.type === 'boolean' ? 12 : 24} key={field.key}><Form.Item name={field.key} label={field.label} valuePropName={field.type === 'boolean' ? 'checked' : 'value'}><FieldControl field={field} /></Form.Item></Col>)}</Row></div>)}<Button htmlType="submit" type="primary" size="large" block loading={running} icon={<SafetyCertificateOutlined />} className="primary-green">{selectedProject && !creating ? '保存并重新体检' : '创建项目并开始体检'}</Button></Form></Card></Col>
      <Col xs={24} xl={15}><Card className="work-card" title="02 · 可审计体检报告" extra={report ? <Tag color="green">已生成</Tag> : <Tag>尚未体检</Tag>}><div className="status-strip"><div className="status-mini"><Text type="secondary">通过</Text><strong style={{ color: '#287342' }}>{summary.pass}</strong></div><div className="status-mini"><Text type="secondary">不满足</Text><strong style={{ color: '#b63c34' }}>{summary.fail}</strong></div><div className="status-mini"><Text type="secondary">待确认</Text><strong style={{ color: '#a36e12' }}>{summary.pending}</strong></div><div className="status-mini"><Text type="secondary">提示</Text><strong style={{ color: '#356c9b' }}>{summary.advisory}</strong></div></div>{report ? <><Descriptions size="small" column={2} bordered style={{ marginBottom: 14 }}><Descriptions.Item label="项目">{report.project.name}</Descriptions.Item><Descriptions.Item label="本次检查">{report.run_id?.slice(0, 8)}</Descriptions.Item></Descriptions><List dataSource={report.results} pagination={{ pageSize: 8, hideOnSinglePage: true }} renderItem={item => <ResultItem key={item.id || `${item.title}-${item.parameter_key}`} item={item} />} /></> : <Empty description="先录入项目条件并执行体检；系统会生成带条文证据的检查清单。" image={Empty.PRESENTED_IMAGE_SIMPLE} />}</Card></Col>
    </Row>
  </div>
}
