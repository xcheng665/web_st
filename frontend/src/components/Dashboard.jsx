import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, List, Row, Space, Statistic, Tag, Typography } from 'antd'
import {
  ApiOutlined,
  ArrowRightOutlined,
  BookOutlined,
  ClusterOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

const { Title, Text, Paragraph } = Typography

export default function Dashboard({ onUpload }) {
  const [data, setData] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    axios.get('/api/dashboard').then(response => setData(response.data))
  }, [])

  if (!data) return <div style={{ padding: 40 }}>正在加载工作台…</div>

  const metrics = [
    { label: '规范库', value: data.metrics.specifications, icon: <BookOutlined />, color: '#1f6f6b', note: '已导入标准文件' },
    { label: '条文总量', value: data.metrics.articles, icon: <FileTextOutlined />, color: '#b56a35', note: '可检索与可抽取' },
    { label: '知识实体', value: data.metrics.entities, icon: <ClusterOutlined />, color: '#356c9b', note: '图谱节点沉淀' },
    { label: '待审核标注', value: data.metrics.pending_annotations, icon: <ApiOutlined />, color: '#9b5e4e', note: '需要人工把关' },
  ]

  const actions = [
    { title: '配置模型', desc: '填入 API Key，连接 OpenAI 兼容模型', path: '/settings' },
    { title: '批量抽取', desc: '选择规范，生成待审核标注', path: '/settings' },
    { title: '审阅图谱', desc: '查看实体、关系和原文证据', path: '/knowledge_graph' },
    { title: '方案体检', desc: '录入项目条件，输出合规清单', path: '/compliance' },
  ]

  return <div>
    <section className="hero-panel">
      <div style={{ maxWidth: 760, position: 'relative', zIndex: 2 }}>
        <div className="page-kicker" style={{ color: '#f1d08d' }}>KNOWLEDGE-DRIVEN DESIGN REVIEW</div>
        <Title level={1} style={{ margin: 0, fontFamily: 'STKaiti, KaiTi, serif' }}>让规范真正参与设计决策</Title>
        <Paragraph style={{ color: '#dbe7df', fontSize: 15, margin: '10px 0 18px' }}>
          平台把条文、实体、关系、证据和项目参数串成一条可追溯链路：从导入规范，到 LLM 标注审核，再到图谱展示与方案阶段合规体检。
        </Paragraph>
        <div className="hero-actions">
          <Button size="large" type="primary" ghost icon={<ThunderboltOutlined />} onClick={() => navigate('/compliance')}>开始方案体检</Button>
          <Button size="large" onClick={onUpload}>导入规范文件</Button>
          <Button size="large" type="text" style={{ color: '#fffaf0' }} onClick={() => navigate('/knowledge_graph')}>查看知识图谱 <ArrowRightOutlined /></Button>
        </div>
      </div>
    </section>

    {!data.llm.configured && <Alert
      showIcon
      type="warning"
      message="尚未配置 LLM 模型"
      description="配置模型后可对条文进行自动标注，并在审核后写入知识图谱。"
      action={<Button size="small" icon={<SettingOutlined />} onClick={() => navigate('/settings')}>配置模型</Button>}
      style={{ marginBottom: 18, borderRadius: 16 }}
    />}

    <Row gutter={[16, 16]}>
      {metrics.map(metric => <Col xs={24} sm={12} lg={6} key={metric.label}>
        <Card className="metric-card" style={{ '--metric-color': metric.color }}>
          <Space align="start" style={{ width: '100%', justifyContent: 'space-between' }}>
            <Statistic title={metric.label} value={metric.value} valueStyle={{ color: '#183a37', fontWeight: 700 }} />
            <div className="metric-icon" style={{ '--metric-color': metric.color }}>{metric.icon}</div>
          </Space>
          <div className="metric-footer">数据来源：{metric.note}</div>
        </Card>
      </Col>)}
    </Row>

    <Row gutter={[16, 16]} style={{ marginTop: 18 }}>
      <Col xs={24} xl={14}>
        <Card className="work-card" title="继续工作" extra={<Tag color="gold">推荐流程</Tag>}>
          <div className="action-grid">
            {actions.map(action => <Button className="action-tile" key={action.title} onClick={() => navigate(action.path)}>
              <strong>{action.title}</strong>
              <span>{action.desc}</span>
            </Button>)}
          </div>
        </Card>
      </Col>
      <Col xs={24} xl={10}>
        <Card className="work-card" title="平台能力状态">
          <List size="small" dataSource={[
            ['API 配置', data.llm.configured ? '已配置' : '待配置', data.llm.configured ? 'green' : 'gold'],
            ['图谱节点', `${data.metrics.entities} 个实体`, data.metrics.entities ? 'cyan' : 'default'],
            ['审核队列', `${data.metrics.pending_annotations} 条待审核`, data.metrics.pending_annotations ? 'gold' : 'green'],
            ['合规体检', data.recent_projects?.length ? '已有项目档案' : '可创建示例项目', data.recent_projects?.length ? 'purple' : 'blue'],
          ]} renderItem={item => <List.Item><Tag color={item[2]}>{item[1]}</Tag>{item[0]}</List.Item>} />
        </Card>
      </Col>
    </Row>

    <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
      <Col xs={24} xl={10}>
        <Card className="work-card" title="最近导入规范">
          <List dataSource={data.specifications} locale={{ emptyText: '还没有导入规范' }} renderItem={item => <List.Item actions={[<Button type="link" onClick={() => navigate(`/specifications/${item.id}/articles`)}>进入条文</Button>]}>
            <List.Item.Meta title={<><Tag color="geekblue">{item.code}</Tag>{item.name}</>} description={`共 ${item.articles} 条；已入图 ${item.tagged_articles} 条`} />
          </List.Item>} />
        </Card>
      </Col>
      <Col xs={24} xl={7}>
        <Card className="work-card" title={`待审核标注 (${data.metrics.pending_annotations})`}>
          <List size="small" dataSource={data.pending || []} locale={{ emptyText: '当前没有待审核标注' }} renderItem={annotation => <List.Item>
            <Space><Tag color="gold">待审核</Tag><FileSearchOutlined />条文 #{annotation.article_id}</Space>
          </List.Item>} />
        </Card>
      </Col>
      <Col xs={24} xl={7}>
        <Card className="work-card" title="最近项目体检">
          <List size="small" dataSource={data.recent_projects || []} locale={{ emptyText: '尚未创建项目档案' }} renderItem={project => <List.Item actions={[<Button type="link" onClick={() => navigate('/compliance')}>继续</Button>]}>
            <Tag color="purple">项目</Tag>{project.name}
          </List.Item>} />
        </Card>
      </Col>
    </Row>
  </div>
}
