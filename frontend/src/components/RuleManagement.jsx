import { useState, useEffect } from 'react'
import { Table, Button, Card, Tag, Typography, message, Space, Modal, Form, Input, Select } from 'antd'
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined,
  FileTextOutlined
} from '@ant-design/icons'
import axios from 'axios'

const { Title } = Typography
const { TextArea } = Input

function RuleManagement() {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchRules()
  }, [])

  const fetchRules = async () => {
    setLoading(true)
    try {
      const response = await axios.get('/api/rules')
      setRules(response.data)
    } catch (error) {
      message.error('获取规则列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingRule(null)
    form.resetFields()
    setShowModal(true)
  }

  const handleEdit = (rule) => {
    setEditingRule(rule)
    form.setFieldsValue({
      name: rule.name,
      rule_type: rule.rule_type,
      content: rule.content
    })
    setShowModal(true)
  }

  const handleDelete = async (ruleId) => {
    try {
      await axios.delete(`/api/rules/${ruleId}`)
      message.success('删除成功')
      fetchRules()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values) => {
    try {
      if (editingRule) {
        await axios.put(`/api/rules/${editingRule.id}`, values)
        message.success('修改成功')
      } else {
        await axios.post('/api/rules', values)
        message.success('添加成功')
      }
      setShowModal(false)
      fetchRules()
    } catch (error) {
      message.error(editingRule ? '修改失败' : '添加失败')
    }
  }

  const columns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '规则类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      render: (text) => <Tag color="green">{text}</Tag>
    },
    {
      title: '规则内容',
      dataIndex: 'content',
      key: 'content',
      render: (text) => (
        <div style={{ maxWidth: '500px', wordBreak: 'break-all' }}>
          {text.length > 100 ? text.substring(0, 100) + '...' : text}
        </div>
      )
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

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <FileTextOutlined style={{ fontSize: '24px', marginRight: '10px', color: '#1890ff' }} />
          <Title level={2}>规则管理</Title>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加规则
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={rules}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          bordered
          title={() => '规则列表'}
          emptyText="暂无规则数据"
        />
      </Card>

      <Modal
        title={editingRule ? '编辑规则' : '添加规则'}
        open={showModal}
        onCancel={() => setShowModal(false)}
        footer={null}
        width={600}
      >
        <Form form={form} onFinish={handleSubmit} layout="vertical">
          <Form.Item
            label="规则名称"
            name="name"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="例如：高层建筑高度约束" />
          </Form.Item>
          <Form.Item
            label="规则类型"
            name="rule_type"
          >
            <Select
              placeholder="选择规则类型"
              options={[
                { value: '约束规则', label: '约束规则' },
                { value: '推理规则', label: '推理规则' },
                { value: '计算规则', label: '计算规则' },
                { value: '验证规则', label: '验证规则' },
                { value: '其他', label: '其他' }
              ]}
              defaultValue="约束规则"
            />
          </Form.Item>
          <Form.Item
            label="规则内容"
            name="content"
            rules={[{ required: true, message: '请输入规则内容' }]}
          >
            <TextArea 
              placeholder="描述规则的具体内容...\n例如：IF 建筑高度 > 27m THEN 属于 高层建筑" 
              rows={5} 
            />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingRule ? '保存修改' : '添加'}
              </Button>
              <Button onClick={() => setShowModal(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default RuleManagement
