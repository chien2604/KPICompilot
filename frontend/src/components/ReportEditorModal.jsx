import { Alert, Input, Modal, Space, Tabs, Typography, message } from 'antd';
import { useEffect, useState } from 'react';

const { Text } = Typography;

export default function ReportEditorModal({ open, report, onClose, onSave }) {
  const [content, setContent] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (report) {
      setContent(report.content || '');
    }
  }, [report]);

  const save = async () => {
    setSaving(true);
    try {
      await onSave(content);
      message.success('Đã lưu thay đổi báo cáo');
      onClose();
    } catch (error) {
      message.error('Không lưu được thay đổi báo cáo');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Chỉnh sửa báo cáo (HTML)"
      open={open}
      onCancel={onClose}
      width={820}
      onOk={save}
      okText="Lưu thay đổi"
      okButtonProps={{ loading: saving }}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message="Sửa trực tiếp mã HTML của báo cáo. Giữ nguyên cấu trúc tiêu ngữ và các thẻ h2/h3/table/ul để đảm bảo hiển thị đúng khi xuất PDF/Word."
        />
        <Tabs
          items={[
            {
              key: 'edit',
              label: 'Mã HTML',
              children: (
                <Input.TextArea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  autoSize={{ minRows: 16, maxRows: 24 }}
                  style={{ fontFamily: 'ui-monospace, monospace', fontSize: 13 }}
                />
              ),
            },
            {
              key: 'preview',
              label: 'Xem trước',
              children: (
                <div
                  className="report-content"
                  style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, maxHeight: 480, overflowY: 'auto' }}
                  dangerouslySetInnerHTML={{ __html: content }}
                />
              ),
            },
          ]}
        />
      </Space>
    </Modal>
  );
}
