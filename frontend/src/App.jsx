import { lazy, Suspense, useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { ConfigProvider, Layout, Menu, Typography, Spin, message } from 'antd'
import { ReadOutlined, ShareAltOutlined, DatabaseOutlined, BarChartOutlined, DashboardOutlined, SettingOutlined, SafetyCertificateOutlined, DiffOutlined, FileDoneOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Header, Content, Sider } = Layout
const { Title } = Typography
const Dashboard = lazy(() => import('./components/Dashboard'))
const SpecificationList = lazy(() => import('./components/SpecificationList'))
const ArticleList = lazy(() => import('./components/ArticleList'))
const KnowledgeGraph = lazy(() => import('./components/KnowledgeGraph'))
const ComplianceWorkbench = lazy(() => import('./components/ComplianceWorkbench'))
const StandardComparison = lazy(() => import('./components/StandardComparison'))
const AnnotationReviewWorkbench = lazy(() => import('./components/AnnotationReviewWorkbench'))
const EntityManagement = lazy(() => import('./components/EntityManagement'))
const RelationManagement = lazy(() => import('./components/RelationManagement'))
const RuleManagement = lazy(() => import('./components/RuleManagement'))
const ModelSettings = lazy(() => import('./components/ModelSettings'))
const UploadModal = lazy(() => import('./components/UploadModal'))

function Workspace() {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({})
  const [showUpload, setShowUpload] = useState(false)

  const fetchStats = async () => {
    try { setStats((await axios.get('/api/stats')).data) }
    catch { message.error('获取统计数据失败') }
    finally { setLoading(false) }
  }
  useEffect(() => { fetchStats() }, [])
  const rootPath = location.pathname.split('/')[1] || 'specifications'
  const menuItems = [
    { key: 'dashboard', icon: <DashboardOutlined />, label: '工作台' },
    { key: 'specifications', icon: <ReadOutlined />, label: '规范库' },
    { key: 'knowledge_graph', icon: <ShareAltOutlined />, label: '知识模型' },
    { key: 'compliance', icon: <SafetyCertificateOutlined />, label: '合规体检' },
    { key: 'comparison', icon: <DiffOutlined />, label: '规范对比' },
    { key: 'review', icon: <FileDoneOutlined />, label: '标注审核' },
    { key: 'entities', icon: <DatabaseOutlined />, label: '实体库' },
    { key: 'relations', icon: <BarChartOutlined />, label: '关系库' },
    { key: 'rules', icon: <BarChartOutlined />, label: '规则库' },
    { key: 'settings', icon: <SettingOutlined />, label: '模型配置' },
  ]
  if (loading) return <div style={{ height: '100vh', display: 'grid', placeItems: 'center' }}><Spin size="large" /></div>

  return <ConfigProvider theme={{ token: { colorPrimary: '#183a37', borderRadius: 12, fontFamily: 'Microsoft YaHei, PingFang SC, sans-serif' }, components: { Card: { headerFontSize: 16 }, Menu: { darkItemSelectedBg: '#d7b56d', darkItemSelectedColor: '#183a37' } } }}>
  <Layout className="app-shell">
    <video className="app-background-video" autoPlay muted loop playsInline preload="metadata" aria-hidden="true">
      <source src="/hacker-apartment-rainy-evening.mp4" type="video/mp4" />
    </video>
    <Header className="app-header">
      <div className="brand-lockup">
        <div className="brand-mark"><ReadOutlined style={{ fontSize: 24 }} /></div>
        <div><Title level={3} className="brand-title">建筑设计规范 · 知识模型</Title><span className="brand-subtitle">BUILDING CODE INTELLIGENCE</span></div>
      </div>
      <div className="top-stats"><span className="top-stat">规范<strong>{stats.specifications || 0}</strong></span><span className="top-stat">条文<strong>{stats.articles || 0}</strong></span><span className="top-stat">实体<strong>{stats.entities || 0}</strong></span><span className="top-stat">关系<strong>{stats.relations || 0}</strong></span></div>
    </Header>
    <Layout>
      <Sider className="side-nav" collapsible collapsed={collapsed} onCollapse={setCollapsed} width={198}>
        <Menu theme="dark" mode="inline" selectedKeys={[rootPath]} style={{ height: '100%', background: 'transparent' }} items={menuItems} onClick={({ key }) => navigate(`/${key}`)} />
      </Sider>
      <Layout className="app-content-wrap"><Content className="page-surface">
        <Suspense fallback={<div style={{ padding: 40 }}>正在加载页面…</div>}><Routes>
          <Route path="/" element={<Navigate to="/dashboard" />} />
          <Route path="/dashboard" element={<Dashboard onUpload={() => setShowUpload(true)} />} />
          <Route path="/specifications" element={<SpecificationList onUpload={() => setShowUpload(true)} />} />
          <Route path="/specifications/:specId/articles" element={<ArticleList />} />
          <Route path="/knowledge_graph" element={<KnowledgeGraph />} />
          <Route path="/compliance" element={<ComplianceWorkbench />} />
          <Route path="/comparison" element={<StandardComparison />} />
          <Route path="/review" element={<AnnotationReviewWorkbench />} />
          <Route path="/entities" element={<EntityManagement />} /><Route path="/relations" element={<RelationManagement />} /><Route path="/rules" element={<RuleManagement />} />
          <Route path="/settings" element={<ModelSettings />} />
        </Routes></Suspense>
      </Content></Layout>
    </Layout>
    {showUpload && <Suspense fallback={null}><UploadModal visible={showUpload} onCancel={() => setShowUpload(false)} onSuccess={() => { fetchStats(); setShowUpload(false); message.success('文件上传成功') }} /></Suspense>}
  </Layout>
  </ConfigProvider>
}
export default function App() { return <BrowserRouter><Workspace /></BrowserRouter> }
