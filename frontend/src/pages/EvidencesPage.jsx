import { Button, Card, Form, Select, Space, Typography, Upload, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { evidenceApi } from '../api/evidenceApi';
import { taskApi } from '../api/taskApi';
import EvidenceTable from '../components/EvidenceTable';

export default function EvidencesPage() {
  const [evidences, setEvidences] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [file, setFile] = useState(null);
  const [form] = Form.useForm();
  const load = () => evidenceApi.list().then(setEvidences);
  useEffect(() => { load(); taskApi.list().then(setTasks); }, []);

  const upload = async () => {
    const values = await form.validateFields();
    if (!file) return message.warning('Chọn file minh chứng');
    await evidenceApi.upload({ task_id: values.task_id, uploaded_by: localStorage.getItem('selected_user_id') || 1, file });
    message.success('Đã upload và phân tích minh chứng');
    setFile(null);
    form.resetFields();
    load();
  };

  return (
    <Space direction="vertical" size={18} className="page">
      <Typography.Title level={3}>Minh chứng Công việc</Typography.Title>
      <Card title="Upload minh chứng">
        <Form layout="inline" form={form}>
          <Form.Item name="task_id" rules={[{ required: true }]} className="wide-form-item">
            <Select showSearch placeholder="Chọn nhiệm vụ" options={tasks.map((t) => ({ value: t.id, label: `${t.id} - ${t.title}` }))} />
          </Form.Item>
          <Upload beforeUpload={(selected) => { setFile(selected); return false; }} maxCount={1}>
            <Button icon={<UploadOutlined />}>Chọn file</Button>
          </Upload>
          <Button type="primary" onClick={upload}>Upload</Button>
        </Form>
      </Card>
      <Card>
        <EvidenceTable data={evidences} />
      </Card>
    </Space>
  );
}
