import { Card, Empty } from 'antd';

export default function ReportPreview({ report }) {
  if (!report) return <Empty description="Chưa chọn báo cáo" />;
  return (
    <Card title={`${report.report_type} - ${report.period}`}>
      <div className="report-content" dangerouslySetInnerHTML={{ __html: report.content }} />
    </Card>
  );
}
