import { useState, useEffect } from 'react'
import { Table, Button, Card, Tag, Typography, message, Space, Modal, Form, Input, Select } from 'antd'
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined,
  BarChartOutlined
} from '@ant-design/icons'
import axios from 'axios'

const { Title } = Typography
const { TextArea } = Input

function RelationManagement() {
  const [relations, setRelations] = useState([])
  const [entities, setEntities] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingRelation, setEditingRelation] = useState(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchRelations()
    fetchEntities()
  }, [])

  const fetchRelations = async () => {
    setLoading(true)
    try {
      const response = await axios.get('/api/relations')
      setRelations(response.data)
    } catch (error) {
      message.error('获取关系列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchEntities = async () => {
    try {
      const response = await axios.get('/api/entities')
      setEntities(response.data)
    } catch (error) {
      message.error('获取实体列表失败')
    }
  }

  const handleAdd = () => {
    setEditingRelation(null)
    form.resetFields()
    setShowModal(true)
  }

  const handleEdit = (relation) => {
    setEditingRelation(relation)
    form.setFieldsValue({
      source_id: relation.source_id,
      target_id: relation.target_id,
      relation_type: relation.relation_type,
      description: relation.description || ''
    })
    setShowModal(true)
  }

  const handleDelete = async (relationId) => {
    try {
      await axios.delete(`/api/relations/${relationId}`)
      message.success('删除成功')
      fetchRelations()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values) => {
    try {
      if (editingRelation) {
        await axios.put(`/api/relations/${editingRelation.id}`, values)
        message.success('修改成功')
      } else {
        await axios.post('/api/relations', values)
        message.success('添加成功')
      }
      setShowModal(false)
      fetchRelations()
    } catch (error) {
      message.error(editingRelation ? '修改失败' : '添加失败')
    }
  }

  const columns = [
    {
      title: '源节点',
      dataIndex: 'source_name',
      key: 'source_name',
      render: (text) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '关系类型',
      dataIndex: 'relation_type',
      key: 'relation_type',
      render: (text) => <Tag color="orange">{text}</Tag>
    },
    {
      title: '目标节点',
      dataIndex: 'target_name',
      key: 'target_name',
      render: (text) => <Tag color="green">{text}</Tag>
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (text) => text || '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) => new Date(text).toLocaleDateString()
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>
            删除
          </Button>
        </Space>
      )
    }
  ]

  const entityOptions = entities.map(entity => ({
    value: entity.id,
    label: entity.name
  }))

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <BarChartOutlined style={{ fontSize: '24px', marginRight: '10px', color: '#1890ff' }} />
          <Title level={2}>关系管理</Title>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加关系
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={relations}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          bordered
          title={() => '关系列表'}
          emptyText="暂无关系数据，请先添加实体和关系"
        />
      </Card>

      <Modal
        title={editingRelation ? '编辑关系' : '添加关系'}
        open={showModal}
        onCancel={() => setShowModal(false)}
        footer={null}
      >
        <Form form={form} onFinish={handleSubmit} layout="vertical">
          <Form.Item
            label="源节点"
            name="source_id"
            rules={[{ required: true, message: '请选择源节点' }]}
          >
            <Select
              placeholder="选择源节点"
              options={entityOptions}
            />
          </Form.Item>
          <Form.Item
            label="目标节点"
            name="target_id"
            rules={[{ required: true, message: '请选择目标节点' }]}
          >
            <Select
              placeholder="选择目标节点"
              options={entityOptions}
            />
          </Form.Item>
          <Form.Item
            label="关系类型"
            name="relation_type"
            rules={[{ required: true, message: '请输入关系类型' }]}
          >
            <Input placeholder="例如：属于、包含、大于" />
          </Form.Item>
          <Form.Item
            label="描述"
            name="description"
          >
            <TextArea placeholder="描述该关系的含义..." rows={3} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingRelation ? '保存修改' : '添加'}
              </Button>
              <Button onClick={() => setShowModal(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default RelationManagement
