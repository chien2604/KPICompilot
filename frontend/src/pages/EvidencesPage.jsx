import { Button, Card, Form, Select, Space, Tag, Typography, Upload, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { useEffect, useMemo, useState } from 'react';
import { evidenceApi } from '../api/evidenceApi';
import { taskApi } from '../api/taskApi';
import { useAuth } from '../contexts/AuthContext';
import EvidenceTable from '../components/EvidenceTable';

export default function EvidencesPage() {
  const { user } = useAuth();
  const myId = user?.user_id;
  const canAssign = user?.level <= 4;

  const [evidences, setEvidences]     = useState([]);
  const [myTasks, setMyTasks]         = useState([]);   // task được giao cho mình
  const [assignedTasks, setAssignedTasks] = useState([]); // task mình đã giao
  const [file, setFile]               = useState(null);
  const [uploading, setUploading]     = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [form]                        = Form.useForm();

  const loadAll = () => {
    if (!myId) return;
    setTableLoading(true);
    const requests = [
      evidenceApi.list({ uploaded_by: myId }),
      taskApi.list({ assigned_user_id: myId }),
    ];
    if (canAssign) requests.push(taskApi.list({ creator_id: myId }));

    Promise.all(requests)
      .then(([evidenceList, assigned, created]) => {
        setEvidences(evidenceList);
        setMyTasks(assigned);
        setAssignedTasks(created || []);
      })
      .catch(console.error)
      .finally(() => setTableLoading(false));
  };

  useEffect(() => { loadAll(); }, [myId]);

  // Gộp task + gắn nhãn, loại trùng id
  const allTaskOptions = useMemo(() => {
    const seen = new Set();
    const opts = [];

    myTasks.forEach((t) => {
      if (!seen.has(t.id)) {
        seen.add(t.id);
        opts.push({ value: t.id, label: `[Phụ trách] ${t.id} – ${t.title}`, group: 'mine' });
      }
    });

    assignedTasks.forEach((t) => {
      if (!seen.has(t.id)) {
        seen.add(t.id);
        opts.push({ value: t.id, label: `[Đã giao] ${t.id} – ${t.title}`, group: 'assigned' });
      }
    });

    return opts;
  }, [myTasks, assignedTasks]);

  // Nhóm theo "Phụ trách" / "Đã giao"
  const taskSelectOptions = useMemo(() => {
    const groups = [];
    const mine = allTaskOptions.filter((o) => o.group === 'mine');
    const assigned = allTaskOptions.filter((o) => o.group === 'assigned');
    if (mine.length) groups.push({ label: 'Nhiệm vụ phụ trách', options: mine });
    if (assigned.length) groups.push({ label: 'Nhiệm vụ đã giao', options: assigned });
    return groups;
  }, [allTaskOptions]);

  const upload = async () => {
    let values;
    try { values = await form.validateFields(); }
    catch { return; }
    if (!file) return message.warning('Chọn file minh chứng');

    setUploading(true);
    try {
      await evidenceApi.upload({ task_id: values.task_id, uploaded_by: myId, file });
      message.success('Đã upload và phân tích minh chứng');
      setFile(null);
      form.resetFields();
      loadAll();
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
          <Form.Item
            name="task_id"
            rules={[{ required: true, message: 'Chọn nhiệm vụ' }]}
            className="wide-form-item"
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="Chọn nhiệm vụ..."
              style={{ minWidth: 360 }}
              options={taskSelectOptions}
              optionRender={(opt) => (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {opt.data.group === 'assigned'
                      ? opt.data.label.replace('[Đã giao] ', '')
                      : opt.data.label.replace('[Phụ trách] ', '')}
                  </span>
                  <Tag
                    style={{ margin: 0, borderRadius: 20, flexShrink: 0 }}
                    color={opt.data.group === 'assigned' ? 'gold' : 'blue'}
                  >
                    {opt.data.group === 'assigned' ? 'Đã giao' : 'Phụ trách'}
                  </Tag>
                </div>
              )}
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

          <Button type="primary" onClick={upload} loading={uploading}>
            Upload
          </Button>
        </Form>

        {/* Thống kê nhanh */}
        <div style={{ marginTop: 12, fontSize: 13, color: '#64748b' }}>
          {myTasks.length > 0 && <span>{myTasks.length} việc phụ trách</span>}
          {canAssign && assignedTasks.length > 0 && (
            <span style={{ marginLeft: 16 }}>{assignedTasks.length} việc đã giao</span>
          )}
        </div>
      </Card>

      <Card>
        <EvidenceTable data={evidences} loading={tableLoading} />
      </Card>
    </Space>
  );
}
