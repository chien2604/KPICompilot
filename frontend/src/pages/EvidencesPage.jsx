import { Button, Card, Form, Select, Space, Typography, Upload, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { evidenceApi } from '../api/evidenceApi';
import { taskApi } from '../api/taskApi';
import EvidenceTable from '../components/EvidenceTable';

const getSelectedUserId = () => localStorage.getItem('selected_user_id') || '1';

export default function EvidencesPage() {
  const [evidences, setEvidences] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState(getSelectedUserId());
  const [form] = Form.useForm();

  const refreshForUser = (userId) => {
    const numericUserId = Number(userId);
    form.resetFields(['task_id']);
    setTableLoading(true);
    
    Promise.all([
      evidenceApi.list({ uploaded_by: numericUserId }),
      taskApi.list({ assigned_user_id: numericUserId })
    ])
      .then(([evidenceList, taskList]) => {
        setEvidences(evidenceList);
        setTasks(taskList);
      })
      .catch((err) => {
        console.error(err);
      })
      .finally(() => {
        setTableLoading(false);
      });
  };

  useEffect(() => {
    refreshForUser(selectedUserId);
    const handleUserChange = (event) => {
      const nextUserId = String(event.detail || getSelectedUserId());
      setSelectedUserId(nextUserId);
      refreshForUser(nextUserId);
    };
    window.addEventListener('demo-user-change', handleUserChange);
    return () => window.removeEventListener('demo-user-change', handleUserChange);
  }, []);

  const upload = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch (err) {
      return;
    }
    if (!file) return message.warning('Chọn file minh chứng');
    
    setUploading(true);
    try {
      await evidenceApi.upload({ task_id: values.task_id, uploaded_by: selectedUserId, file });
      message.success('Đã upload và phân tích minh chứng');
      setFile(null);
      form.resetFields();
      refreshForUser(selectedUserId);
    } catch (err) {
      console.error(err);
      message.error('Gặp lỗi khi tải lên hoặc phân tích minh chứng');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Space direction="vertical" size={18} className="page">
      <Typography.Title level={3}>Minh chứng Công việc</Typography.Title>
      <Card title="Upload minh chứng">
        <Form layout="inline" form={form} disabled={uploading}>
          <Form.Item name="task_id" rules={[{ required: true }]} className="wide-form-item">
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="Chọn nhiệm vụ"
              options={tasks.map((t) => ({ value: t.id, label: `${t.id} - ${t.title}` }))}
            />
          </Form.Item>
          <Upload 
            beforeUpload={(selected) => { setFile(selected); return false; }} 
            maxCount={1}
            fileList={file ? [file] : []}
            onRemove={() => setFile(null)}
          >
            <Button icon={<UploadOutlined />}>Chọn file</Button>
          </Upload>
          <Button type="primary" onClick={upload} loading={uploading}>Upload</Button>
        </Form>
      </Card>
      <Card>
        <EvidenceTable data={evidences} loading={tableLoading} />
      </Card>
    </Space>
  );
}
