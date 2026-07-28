import { useState, useEffect } from 'react'
import { Table, Button, Card, Tag, Typography, message, Space, Modal, Form, Input, Select } from 'antd'
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined,
  DatabaseOutlined
} from '@ant-design/icons'
import axios from 'axios'

const { Title } = Typography
const { TextArea } = Input

function EntityManagement() {
  const [entities, setEntities] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingEntity, setEditingEntity] = useState(null)
  const [form] = Form.useForm()
  const [aliasForm] = Form.useForm()
  const [aliasEntity, setAliasEntity] = useState(null)

  useEffect(() => {
    fetchEntities()
  }, [])

  const fetchEntities = async () => {
    setLoading(true)
    try {
      const response = await axios.get('/api/entities')
      setEntities(response.data)
    } catch (error) {
      message.error('获取实体列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingEntity(null)
    form.resetFields()
    setShowModal(true)
  }

  const handleEdit = (entity) => {
    setEditingEntity(entity)
    form.setFieldsValue({
      name: entity.name,
      entity_type: entity.entity_type,
      description: entity.description || ''
    })
    setShowModal(true)
  }

  const handleDelete = async (entityId) => {
    try {
      await axios.delete(`/api/entities/${entityId}`)
      message.success('删除成功')
      fetchEntities()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const manageAliases = (entity) => {
    setAliasEntity(entity)
    aliasForm.resetFields()
  }

  const addAlias = async (values) => {
    try {
      await axios.post(`/api/entities/${aliasEntity.id}/aliases`, values)
      message.success('别名已归并到该实体')
      await fetchEntities()
      const updated = (await axios.get(`/api/entities/${aliasEntity.id}`)).data
      setAliasEntity(updated)
      aliasForm.resetFields()
    } catch (error) { message.error(error.response?.data?.error || '添加别名失败') }
  }

  const removeAlias = async (alias) => {
    try {
      await axios.delete(`/api/entity-aliases/${alias.id}`)
      message.success('别名已删除')
      await fetchEntities()
      const updated = (await axios.get(`/api/entities/${aliasEntity.id}`)).data
      setAliasEntity(updated)
    } catch { message.error('删除别名失败') }
  }

  const handleSubmit = async (values) => {
    try {
      if (editingEntity) {
        await axios.put(`/api/entities/${editingEntity.id}`, values)
        message.success('修改成功')
      } else {
        await axios.post('/api/entities', values)
        message.success('添加成功')
      }
      setShowModal(false)
      fetchEntities()
    } catch (error) {
      message.error(editingEntity ? '修改失败' : '添加失败')
    }
  }

  const columns = [
    {
      title: '实体名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '实体类型',
      dataIndex: 'entity_type',
      key: 'entity_type',
      render: (text) => <Tag color="green">{text}</Tag>
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (text) => text || '-'
    },
    {
      title: '别名归并',
      dataIndex: 'aliases',
      key: 'aliases',
      render: (aliases = []) => aliases.length ? aliases.map(alias => <Tag key={alias} color="purple">{alias}</Tag>) : <Typography.Text type="secondary">—</Typography.Text>
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
          <Button size="small" onClick={() => manageAliases(record)}>别名</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>
            删除
          </Button>
        </Space>
      )
    }
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <DatabaseOutlined style={{ fontSize: '24px', marginRight: '10px', color: '#1890ff' }} />
          <Title level={2}>实体管理</Title>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加实体
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={entities}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          bordered
          title={() => '实体列表'}
          emptyText="暂无实体数据"
        />
      </Card>

      <Modal
        title={editingEntity ? '编辑实体' : '添加实体'}
        open={showModal}
        onCancel={() => setShowModal(false)}
        footer={null}
      >
        <Form form={form} onFinish={handleSubmit} layout="vertical">
          <Form.Item
            label="实体名称"
            name="name"
            rules={[{ required: true, message: '请输入实体名称' }]}
          >
            <Input placeholder="例如：建筑高度" />
          </Form.Item>
          <Form.Item
            label="实体类型"
            name="entity_type"
          >
            <Select
              placeholder="选择实体类型"
              options={[
                { value: '实体', label: '实体' },
                { value: '属性', label: '属性' },
                { value: '概念', label: '概念' },
                { value: '约束', label: '约束' },
                { value: '其他', label: '其他' }
              ]}
              defaultValue="实体"
            />
          </Form.Item>
          <Form.Item
            label="描述"
            name="description"
          >
            <TextArea placeholder="描述该实体的含义..." rows={3} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingEntity ? '保存修改' : '添加'}
              </Button>
              <Button onClick={() => setShowModal(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal title={aliasEntity ? `别名归并 · ${aliasEntity.name}` : '别名归并'} open={!!aliasEntity} onCancel={() => setAliasEntity(null)} footer={null}>
        <Typography.Paragraph type="secondary">别名会被自动归并到当前标准实体；原始条文写法仍可追溯。</Typography.Paragraph>
        <Space wrap style={{ marginBottom: 16 }}>{(aliasEntity?.aliases || []).length ? aliasEntity.aliases.map(alias => <Tag key={alias} closable onClose={event => { event.preventDefault(); const found = { id: null, alias }; axios.get(`/api/entities/${aliasEntity.id}/aliases`).then(response => { const item = response.data.find(value => value.alias === alias); if (item) removeAlias(item) }) }}>{alias}</Tag>) : <Typography.Text type="secondary">尚无别名</Typography.Text>}</Space>
        <Form form={aliasForm} layout="inline" onFinish={addAlias}><Form.Item name="alias" rules={[{ required: true, message: '请输入别名' }]}><Input placeholder="例如：居室净高" /></Form.Item><Form.Item><Button type="primary" htmlType="submit">添加并归并</Button></Form.Item></Form>
      </Modal>
    </div>
  )
}

export default EntityManagement
