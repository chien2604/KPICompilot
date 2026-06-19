import { Button, Card, List, Space, Typography, message } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { reportApi } from '../api/reportApi';
import ReportPreview from '../components/ReportPreview';

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [selected, setSelected] = useState(null);
  const load = () => reportApi.list().then((rows) => { setReports(rows); setSelected(rows[0] || null); });
  useEffect(() => {
    load();
  }, []);

  const generate = async () => {
    const report = await reportApi.generate({ report_type: 'WEEKLY', period: '2026-W25', created_by: Number(localStorage.getItem('selected_user_id') || 1) });
    message.success('Đã sinh báo cáo giao ban');
    setSelected(report);
    load();
  };

  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-title-row">
        <Typography.Title level={3}>Báo cáo Tự động</Typography.Title>
        <Button type="primary" icon={<FileTextOutlined />} onClick={generate}>Sinh báo cáo</Button>
      </div>
      <div className="reports-layout">
        <Card title="Danh sách báo cáo" className="reports-list">
          <List dataSource={reports} renderItem={(item) => <List.Item onClick={() => setSelected(item)} className="clickable">{item.report_type} - {item.period}</List.Item>} />
        </Card>
        <ReportPreview report={selected} />
      </div>
    </Space>
  );
}
