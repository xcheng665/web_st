import { useState } from 'react'
import { Modal, Button, Upload, Typography, message, Card, Input, Space } from 'antd'
import { UploadOutlined, FileTextOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Title } = Typography

function UploadModal({ visible, onCancel, onSuccess }) {
  const [loading, setLoading] = useState(false)
  const [previewData, setPreviewData] = useState(null)
  const [specCode, setSpecCode] = useState('')
  const [specName, setSpecName] = useState('')

  const handleUpload = async (file) => {
    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const documentFile = /\.(pdf|docx)$/i.test(file.name)
      if (documentFile && (!specCode.trim() || !specName.trim())) {
        message.warning('导入 PDF、Word 前请填写规范编号和规范名称')
        return
      }
      if (documentFile) {
        formData.append('spec_code', specCode.trim())
        formData.append('spec_name', specName.trim())
      }
      
      const response = await axios.post(documentFile ? '/api/document-import' : '/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      
      message.success(response.data.message)
      setPreviewData(response.data)
      onSuccess()
    } catch (error) {
      message.error(error.response?.data?.error || '上传失败')
    } finally {
      setLoading(false)
    }
  }

  const props = {
    name: 'file',
    accept: '.csv,.xlsx,.xls,.pdf,.docx',
    showUploadList: false,
    beforeUpload: (file) => {
      handleUpload(file)
      return false
    }
  }

  return (
    <Modal
      title="导入规范文件"
      open={visible}
      onCancel={onCancel}
      footer={null}
      width={600}
    >
      <div>
        <Title level={3}>上传规范文件</Title>
        <Typography.Text type="secondary" style={{ display: 'block', marginBottom: '20px' }}>
          支持 CSV、Excel、文字型 PDF 和 Word；文档导入会保留规范编号与提取方式。
        </Typography.Text>

        <Card size="small" title="PDF / Word 来源信息" style={{ marginBottom: 16, background: '#faf5e9' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input value={specCode} onChange={event => setSpecCode(event.target.value)} placeholder="规范编号（例如 GB50096-2011）" />
            <Input value={specName} onChange={event => setSpecName(event.target.value)} placeholder="规范名称（PDF、Word 必填）" />
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>扫描 PDF 若没有文字层，将提示需要配置 Tesseract + Poppler OCR，不会导入空文本。</Typography.Text>
          </Space>
        </Card>

        <Upload {...props}>
          <Button 
            type="primary" 
            icon={<UploadOutlined />} 
            loading={loading}
            size="large"
            style={{ width: '100%' }}
          >
            {loading ? '上传中...' : '点击上传文件'}
          </Button>
        </Upload>

        <Card style={{ marginTop: '20px' }} title="支持的文件格式">
          <div style={{ display: 'flex', gap: '30px' }}>
            <div>
              <FileTextOutlined style={{ fontSize: '24px', marginBottom: '10px', display: 'block' }} />
              <Typography.Text>CSV 文件</Typography.Text>
              <Typography.Text type="secondary" style={{ display: 'block', fontSize: '12px' }}>
                任意列名均可，支持UTF-8、GBK等编码
              </Typography.Text>
            </div>
            <div>
              <FileTextOutlined style={{ fontSize: '24px', marginBottom: '10px', display: 'block' }} />
              <Typography.Text>Excel 文件</Typography.Text>
              <Typography.Text type="secondary" style={{ display: 'block', fontSize: '12px' }}>
                支持 .xlsx 和 .xls 格式
              </Typography.Text>
            </div>
            <div>
              <FileTextOutlined style={{ fontSize: '24px', marginBottom: '10px', display: 'block' }} />
              <Typography.Text>PDF / Word</Typography.Text>
              <Typography.Text type="secondary" style={{ display: 'block', fontSize: '12px' }}>
                提取文字并拆分条文；扫描件进入 OCR 待处理
              </Typography.Text>
            </div>
          </div>
        </Card>

        {previewData && (
          <Card style={{ marginTop: '20px' }} title="上传结果">
            <Typography.Text type="success">
              ✅ {previewData.message}
            </Typography.Text>
            <Typography.Text style={{ display: 'block', marginTop: '10px' }}>
              规范名称: {previewData.spec_name}
            </Typography.Text>
            {previewData.extraction_method && <Typography.Text type="secondary" style={{ display: 'block', marginTop: 6 }}>提取方式: {previewData.extraction_method}</Typography.Text>}
          </Card>
        )}
      </div>
    </Modal>
  )
}

export default UploadModal
