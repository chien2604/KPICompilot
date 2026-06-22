import { Button, Card, List, Popconfirm, Space, Tag, Tooltip, Typography, message } from 'antd';
import { DeleteOutlined, EditOutlined, FilePdfOutlined, FileTextOutlined, FileWordOutlined, RobotOutlined, WarningOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { downloadBlob, reportApi } from '../api/reportApi';
import ReportPreview from '../components/ReportPreview';
import ReportEditorModal from '../components/ReportEditorModal';
function getCurrentISOWeek() {
  const date = new Date();

  const target = new Date(date.valueOf());
  const dayNr = (target.getDay() + 6) % 7;

  target.setDate(target.getDate() - dayNr + 3);

  const firstThursday = new Date(target.getFullYear(), 0, 4);
  const firstThursdayDayNr = (firstThursday.getDay() + 6) % 7;

  firstThursday.setDate(
    firstThursday.getDate() - firstThursdayDayNr + 3
  );

  const weekNumber =
    1 +
    Math.round(
      (target - firstThursday) /
        (7 * 24 * 60 * 60 * 1000)
    );

  return `${target.getFullYear()}-W${String(weekNumber).padStart(2, '0')}`;
}
// CHỦ Ý không có entry "llm" ở đây — khi AI sinh báo cáo thành công ngay lần đầu
// (trường hợp bình thường, đa số lần) thì KHÔNG hiện badge gì cả, vì đây là
// trạng thái mong đợi, không cần làm nổi bật. Chỉ hiện badge cho 2 trường hợp
// đáng chú ý: phải retry, hoặc rơi vào fallback (AI lỗi).
const SOURCE_BADGE = {
  llm_retry: { color: 'blue', icon: <RobotOutlined />, label: 'AI sinh (đã retry)' },
  fallback: { color: 'orange', icon: <WarningOutlined />, label: 'Mẫu cố định (AI lỗi)' },
};

function SourceBadge({ report }) {
  const source = report?.summary_json?._source;
  const config = SOURCE_BADGE[source];
  if (!config) return null;
  const tooltipText = source === 'fallback'
    ? 'AI không trả về HTML hợp lệ sau 2 lần thử, hệ thống dùng mẫu rút gọn. Kiểm tra log backend hoặc GROQ_API_KEY/OPENAI_API_KEY.'
    : 'Lần gọi AI đầu tiên không đúng format, hệ thống đã tự thử lại và thành công.';
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
  const [generating, setGenerating] = useState(false);

  const load = async () => {
    const rows = await reportApi.list();
    setReports(rows);
    return rows;
  };

  useEffect(() => {
    load().then((rows) => {
      setSelected(rows[0] || null);
    });
  }, []);

  const generate = async () => {
    setGenerating(true);
    try {
      const report = await reportApi.generate({
        report_type: 'WEEKLY',
        period: getCurrentISOWeek(),
        created_by: Number(localStorage.getItem('selected_user_id') || 1),
});
      message.success('Đã sinh báo cáo giao ban');
      // Cập nhật state CỤC BỘ ngay với report vừa tạo, không gọi lại load() —
      // gọi load() ngay sau set selected gây race condition: load() là async,
      // khi nó resolve có thể ghi đè selected bằng dữ liệu cũ/stale.
      setReports((prev) => [report, ...prev]);
      setSelected(report);
    } catch (error) {
      // Phân biệt rõ lý do lỗi: timeout (request bị huỷ dù backend vẫn chạy)
      // khác với lỗi thật từ server (4xx/5xx) hoặc lỗi mạng.
      if (error.code === 'ECONNABORTED' || /timeout/i.test(error.message || '')) {
        message.error('Sinh báo cáo mất nhiều thời gian hơn dự kiến. Vui lòng đợi vài giây rồi tải lại trang — báo cáo có thể đã được tạo ở backend.');
      } else if (error?.response?.data?.detail) {
        message.error(`Lỗi từ server: ${error.response.data.detail}`);
      } else {
        message.error(`Không sinh được báo cáo: ${error.message || 'lỗi không xác định'}`);
      }
    } finally {
      setGenerating(false);
    }
  };

  const saveEdit = async (content) => {
    const updated = await reportApi.update(selected.id, content);
    setSelected(updated);
    setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
  };

  const removeReport = async (report) => {
    await reportApi.remove(report.id);
    message.success('Đã xoá báo cáo');
    setReports((prev) => {
      const next = prev.filter((r) => r.id !== report.id);
      if (selected?.id === report.id) {
        setSelected(next[0] || null);
      }
      return next;
    });
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
        <Button type="primary" icon={<FileTextOutlined />} loading={generating} onClick={generate}>
          Sinh báo cáo
        </Button>
      </div>
      <div className="reports-layout">
        <Card title="Danh sách báo cáo" className="reports-list">
          <List
            dataSource={reports}
            renderItem={(item) => (
              <List.Item
                onClick={() => setSelected(item)}
                className={`clickable ${selected?.id === item.id ? 'report-list-item--active' : ''}`}
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
