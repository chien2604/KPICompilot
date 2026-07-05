import { Button, Card, Col, Empty, Row, Space, Tag, Tooltip, Typography, message } from 'antd';
import {
  CalendarOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  FileWordOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusOutlined,
} from '@ant-design/icons';
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
  firstThursday.setDate(firstThursday.getDate() - firstThursdayDayNr + 3);
  const weekNumber = 1 + Math.round((target - firstThursday) / (7 * 24 * 60 * 60 * 1000));
  return `${target.getFullYear()}-W${String(weekNumber).padStart(2, '0')}`;
}

const TYPE_LABEL = { WEEKLY: 'Tuần', MONTHLY: 'Tháng', QUARTERLY: 'Quý' };
const TYPE_COLOR = { WEEKLY: 'blue', MONTHLY: 'green', QUARTERLY: 'purple' };

function ReportListItem({ item, active, onClick, onDelete }) {
  return (
    <div
      className={`report-list-item2 ${active ? 'report-list-item2--active' : ''}`}
      onClick={onClick}
    >
      <div className="report-list-item2__left">
        <div className="report-list-item2__icon">
          <FileTextOutlined />
        </div>
        <div>
          <div className="report-list-item2__period">
            <CalendarOutlined style={{ marginRight: 6, fontSize: 13 }} />
            {item.period}
          </div>
          <Tag
            color={TYPE_COLOR[item.report_type] || 'default'}
            style={{
              marginTop: 4,
              fontSize: 13,
              borderRadius: 6,
              opacity: active ? 0.85 : 1,
            }}
          >
            {TYPE_LABEL[item.report_type] || item.report_type}
          </Tag>
        </div>
      </div>
      <Button
        size="small"
        danger
        type="text"
        icon={<DeleteOutlined />}
        onClick={(e) => { e.stopPropagation(); onDelete(item); }}
        className="report-list-item2__del"
      />
    </div>
  );
}

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [selected, setSelected] = useState(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [exporting, setExporting] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [filterType, setFilterType] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const load = async () => {
    const rows = await reportApi.list();
    setReports(rows);
    return rows;
  };

  useEffect(() => {
    load().then((rows) => setSelected(rows[0] || null));
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
      setReports((prev) => [report, ...prev]);
      setSelected(report);
    } catch (error) {
      if (error.code === 'ECONNABORTED' || /timeout/i.test(error.message || '')) {
        message.error('Sinh báo cáo mất nhiều thời gian. Vui lòng đợi rồi tải lại trang.');
      } else {
        message.error(`Không sinh được báo cáo: ${error?.response?.data?.detail || error.message}`);
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
      if (selected?.id === report.id) setSelected(next[0] || null);
      return next;
    });
  };

  const exportFile = async () => {
    if (!selected) return;
    setExporting('docx');
    try {
      const blob = await reportApi.exportDocx(selected.id);
      downloadBlob(blob, `bao-cao-${selected.period}-${selected.id}.docx`);
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Không xuất được DOCX');
    } finally {
      setExporting(null);
    }
  };

  const filteredReports = filterType ? reports.filter((r) => r.report_type === filterType) : reports;

  return (
    <Space direction="vertical" size={20} className="page">
      <div className="page-title-row">
        <Typography.Title level={3}>Báo cáo Tự động</Typography.Title>
        <Space>
          <Tooltip title={sidebarOpen ? 'Ẩn danh sách' : 'Hiện danh sách'}>
            <Button
              icon={sidebarOpen ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />}
              onClick={() => setSidebarOpen((v) => !v)}
            />
          </Tooltip>
          <Button type="primary" icon={<PlusOutlined />} loading={generating} onClick={generate}>
            Sinh báo cáo mới
          </Button>
        </Space>
      </div>

      <Row gutter={[20, 20]} align="stretch" className="reports-page-row">
        {/* Cột trái — danh sách */}
        {sidebarOpen && (
          <Col xs={24} lg={7} className="reports-sidebar-col">
            <Card
              title={<span style={{ fontSize: 16, fontWeight: 700 }}>Danh sách báo cáo</span>}
              style={{ height: '100%' }}
              bodyStyle={{ padding: '12px 8px' }}
            >
              {/* Bộ lọc loại */}
              <div className="report-type-filter">
                {[null, 'WEEKLY', 'MONTHLY', 'QUARTERLY'].map((type) => (
                  <button
                    key={type ?? 'all'}
                    className={`report-type-btn ${filterType === type ? 'report-type-btn--active' : ''}`}
                    onClick={() => setFilterType(type)}
                    type="button"
                  >
                    {type === null ? 'Tất cả' : TYPE_LABEL[type]}
                  </button>
                ))}
              </div>

              {filteredReports.length === 0 ? (
                <Empty description="Không có báo cáo" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                <div className="report-list2">
                  {filteredReports.map((item) => (
                    <ReportListItem
                      key={item.id}
                      item={item}
                      active={selected?.id === item.id}
                      onClick={() => setSelected(item)}
                      onDelete={removeReport}
                    />
                  ))}
                </div>
              )}
            </Card>
          </Col>
        )}

        {/* Cột phải — preview */}
        <Col xs={24} lg={sidebarOpen ? 17 : 24} className="reports-detail-col">
          <Card
            title={
              selected ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <FileTextOutlined style={{ color: '#1769aa' }} />
                  <span style={{ fontSize: 16, fontWeight: 700 }}>
                    Báo cáo {TYPE_LABEL[selected.report_type] || selected.report_type} — {selected.period}
                  </span>
                  <Tag color={TYPE_COLOR[selected.report_type] || 'default'} style={{ fontSize: 13 }}>
                    {TYPE_LABEL[selected.report_type] || selected.report_type}
                  </Tag>
                </div>
              ) : <span style={{ fontSize: 16, fontWeight: 700 }}>Chi tiết báo cáo</span>
            }
            extra={
              selected && (
                <Space>
                  <Button icon={<EditOutlined />} onClick={() => setEditorOpen(true)}>
                    Sửa nội dung
                  </Button>
                  <Button
                    icon={<FileWordOutlined />}
                    loading={exporting === 'docx'}
                    onClick={exportFile}
                  >
                    Xuất Word
                  </Button>
                </Space>
              )
            }
            style={{ height: '100%' }}
          >
            <ReportPreview report={selected} />
          </Card>
        </Col>
      </Row>

      <ReportEditorModal
        open={editorOpen}
        report={selected}
        onClose={() => setEditorOpen(false)}
        onSave={saveEdit}
      />
    </Space>
  );
}
