import { Button, Card, List, Popconfirm, Space, Tag, Tooltip, Typography, message } from 'antd';
import { DeleteOutlined, EditOutlined, FilePdfOutlined, FileTextOutlined, FileWordOutlined, RobotOutlined, WarningOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { downloadBlob, reportApi } from '../api/reportApi';
import ReportPreview from '../components/ReportPreview';
import ReportEditorModal from '../components/ReportEditorModal';

const SOURCE_BADGE = {
  llm: { color: 'green', icon: <RobotOutlined />, label: 'AI sinh (lần đầu)' },
  llm_retry: { color: 'blue', icon: <RobotOutlined />, label: 'AI sinh (đã retry)' },
  fallback: { color: 'orange', icon: <WarningOutlined />, label: 'Mẫu cố định (AI lỗi)' },
};

function SourceBadge({ report }) {
  const source = report?.summary_json?._source;
  const config = SOURCE_BADGE[source];
  if (!config) return null;
  const tooltipText = source === 'fallback'
    ? 'AI không trả về HTML hợp lệ sau 2 lần thử, hệ thống dùng mẫu rút gọn. Kiểm tra log backend hoặc GROQ_API_KEY/OPENAI_API_KEY.'
    : 'Nội dung được AI phân tích và sinh ra dựa trên số liệu hệ thống theo đúng mẫu báo cáo hành chính.';
  return (
    <Tooltip title={tooltipText}>
      <Tag color={config.color} icon={config.icon}>{config.label}</Tag>
    </Tooltip>
  );
}

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [selected, setSelected] = useState(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [exporting, setExporting] = useState(null); // 'pdf' | 'docx' | null

  const load = () => reportApi.list().then((rows) => {
    setReports(rows);
    setSelected((current) => {
      if (current) {
        const stillExists = rows.find((r) => r.id === current.id);
        if (stillExists) return stillExists;
      }
      return rows[0] || null;
    });
  });

  useEffect(() => {
    load();
  }, []);

  const generate = async () => {
    const report = await reportApi.generate({ report_type: 'WEEKLY', period: '2026-W25', created_by: Number(localStorage.getItem('selected_user_id') || 1) });
    message.success('Đã sinh báo cáo giao ban');
    setSelected(report);
    load();
  };

  const saveEdit = async (content) => {
    const updated = await reportApi.update(selected.id, content);
    setSelected(updated);
    load();
  };

  const removeReport = async (report) => {
    await reportApi.remove(report.id);
    message.success('Đã xoá báo cáo');
    if (selected?.id === report.id) setSelected(null);
    load();
  };

  const exportFile = async (type) => {
    if (!selected) return;
    setExporting(type);
    try {
      const blob = type === 'pdf' ? await reportApi.exportPdf(selected.id) : await reportApi.exportDocx(selected.id);
      const ext = type === 'pdf' ? 'pdf' : 'docx';
      downloadBlob(blob, `bao-cao-${selected.period}-${selected.id}.${ext}`);
    } catch (error) {
      const detail = error?.response?.data?.detail;
      message.error(detail || (type === 'pdf' ? 'Không xuất được PDF (kiểm tra PDF service)' : 'Không xuất được DOCX'));
    } finally {
      setExporting(null);
    }
  };

  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-title-row">
        <Typography.Title level={3}>Báo cáo Tự động</Typography.Title>
        <Button type="primary" icon={<FileTextOutlined />} onClick={generate}>Sinh báo cáo</Button>
      </div>
      <div className="reports-layout">
        <Card title="Danh sách báo cáo" className="reports-list">
          <List
            dataSource={reports}
            renderItem={(item) => (
              <List.Item
                onClick={() => setSelected(item)}
                className="clickable"
                actions={[
                  <Popconfirm
                    key="delete"
                    title="Xoá báo cáo này?"
                    okText="Xoá"
                    cancelText="Huỷ"
                    onConfirm={(e) => { e?.stopPropagation?.(); removeReport(item); }}
                    onCancel={(e) => e?.stopPropagation?.()}
                  >
                    <Button
                      size="small"
                      danger
                      type="text"
                      icon={<DeleteOutlined />}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </Popconfirm>,
                ]}
              >
                {item.report_type} - {item.period}
              </List.Item>
            )}
          />
        </Card>
        <div className="reports-detail">
          {selected && (
            <Space style={{ marginBottom: 12 }} wrap>
              <SourceBadge report={selected} />
              <Button icon={<EditOutlined />} onClick={() => setEditorOpen(true)}>Sửa nội dung</Button>
              <Button icon={<FilePdfOutlined />} loading={exporting === 'pdf'} onClick={() => exportFile('pdf')}>
                Xuất PDF
              </Button>
              <Button icon={<FileWordOutlined />} loading={exporting === 'docx'} onClick={() => exportFile('docx')}>
                Xuất Word
              </Button>
            </Space>
          )}
          <ReportPreview report={selected} />
        </div>
      </div>

      <ReportEditorModal
        open={editorOpen}
        report={selected}
        onClose={() => setEditorOpen(false)}
        onSave={saveEdit}
      />
    </Space>
  );
}
