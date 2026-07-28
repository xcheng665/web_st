import { useState, useEffect } from 'react'
import { Table, Button, Card, Tag, Typography, message, Space } from 'antd'
import { 
  EyeOutlined, 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined,
  ReadOutlined
} from '@ant-design/icons'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

const { Title } = Typography

function SpecificationList({ onUpload }) {
  const [specifications, setSpecifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState(null)
  const [editData, setEditData] = useState({ code: '', name: '' })
  const navigate = useNavigate()

  useEffect(() => {
    fetchSpecifications()
  }, [])

  const fetchSpecifications = async () => {
    setLoading(true)
    try {
      const response = await axios.get('/api/specifications')
      const specs = response.data
      
      const specsWithArticleCount = await Promise.all(
        specs.map(async spec => {
          const articles = await axios.get(`/api/specifications/${spec.id}/articles`)
          return { ...spec, articleCount: articles.data.length }
        })
      )
      setSpecifications(specsWithArticleCount)
    } catch (error) {
      message.error('获取规范列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleViewArticles = (specId) => {
    navigate(`/specifications/${specId}/articles`)
  }

  const handleEdit = (spec) => {
    setEditingId(spec.id)
    setEditData({ code: spec.code, name: spec.name })
  }

  const handleSaveEdit = async (specId) => {
    try {
      await axios.put(`/api/specifications/${specId}`, editData)
      message.success('修改成功')
      setEditingId(null)
      fetchSpecifications()
    } catch (error) {
      message.error('修改失败')
    }
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditData({ code: '', name: '' })
  }

  const handleDelete = async (specId) => {
    try {
      await axios.delete(`/api/specifications/${specId}`)
      message.success('删除成功')
      fetchSpecifications()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const columns = [
    {
      title: '规范编号',
      dataIndex: 'code',
      key: 'code',
      width: 150,
      render: (text, record) => {
        if (editingId === record.id) {
          return (
            <input
              type="text"
              value={editData.code}
              onChange={(e) => setEditData({ ...editData, code: e.target.value })}
              className="ant-input"
              style={{ width: '100%' }}
            />
          )
        }
        return <Tag color="blue">{text}</Tag>
      }
    },
    {
      title: '规范名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => {
        if (editingId === record.id) {
          return (
            <input
              type="text"
              value={editData.name}
              onChange={(e) => setEditData({ ...editData, name: e.target.value })}
              className="ant-input"
              style={{ width: '100%' }}
            />
          )
        }
        return text
      }
    },
    {
      title: '条文数量',
      dataIndex: 'articleCount',
      key: 'articleCount',
      width: 100,
      render: (text) => <Tag color="green">{text}</Tag>
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (text) => new Date(text).toLocaleDateString()
    },
    {
      title: '操作',
      key: 'action',
      width: 250,
      render: (_, record) => {
        if (editingId === record.id) {
          return (
            <Space>
              <Button 
                type="primary" 
                size="small" 
                onClick={() => handleSaveEdit(record.id)}
              >
                保存
              </Button>
              <Button size="small" onClick={handleCancelEdit}>取消</Button>
            </Space>
          )
        }
        return (
          <Space>
            <Button 
              size="small" 
              icon={<EyeOutlined />} 
              onClick={() => handleViewArticles(record.id)}
            >
              查看条文
            </Button>
            <Button 
              size="small" 
              icon={<EditOutlined />} 
              onClick={() => handleEdit(record)}
            >
              编辑
            </Button>
            <Button 
              size="small" 
              danger 
              icon={<DeleteOutlined />} 
              onClick={() => handleDelete(record.id)}
            >
              删除
            </Button>
          </Space>
        )
      }
    }
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <ReadOutlined style={{ fontSize: '24px', marginRight: '10px', color: '#1890ff' }} />
          <Title level={2}>规范管理</Title>
        </div>
        <Button 
          type="primary" 
          icon={<PlusOutlined />}
          onClick={onUpload}
        >
          导入规范文件
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={specifications}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          bordered
          title={() => '规范列表'}
          emptyText="暂无规范数据，点击上方按钮导入规范文件"
        />
      </Card>
    </div>
  )
}

export default SpecificationList
