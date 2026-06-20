import { Button, Card, Descriptions, Progress, Space, Table, Typography, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { kpiApi } from '../api/kpiApi';
import { riskLevelLabel } from '../utils/formatters';

export default function KpiEvaluationPage() {
  const { userId } = useParams();
  const [score, setScore] = useState(null);
  const load = () => kpiApi.score(userId).then(setScore);
  useEffect(() => {
    load();
  }, [userId]);
  const recompute = async () => {
    setScore(await kpiApi.recompute(userId));
    message.success('Rule Engine đã tính lại KPI');
  };
  const rows = score?.breakdown_json?.breakdown || [];
  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-title-row">
        <Typography.Title level={3}>AI Đánh giá KPI</Typography.Title>
        <Button type="primary" icon={<ReloadOutlined />} onClick={recompute}>Tính lại KPI</Button>
      </div>
      <Card>
        <Descriptions column={2}>
          <Descriptions.Item label="Điểm tổng"><Progress type="circle" percent={Math.round(score?.total_score || 0)} /></Descriptions.Item>
          <Descriptions.Item label="Xếp loại">{score?.classification}</Descriptions.Item>
          <Descriptions.Item label="Mức rủi ro">{riskLevelLabel[score?.risk_level] || score?.risk_level}</Descriptions.Item>
          <Descriptions.Item label="Kỳ">{score?.period_month}</Descriptions.Item>
          <Descriptions.Item label="AI giải thích" span={2}><div style={{ whiteSpace: 'pre-wrap' }}>{score?.ai_explanation}</div></Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="Breakdown Rule Engine">
        <Table rowKey="group_name" dataSource={rows} pagination={false} columns={[
          { title: 'Nhóm tiêu chí', dataIndex: 'group_name' },
          { title: 'Điểm tối đa', dataIndex: 'max_score', width: 120 },
          { title: 'Điểm', dataIndex: 'score', width: 120 },
          { title: 'Lý do', dataIndex: 'reasons', render: (items) => items?.join('; ') },
        ]} />
      </Card>
    </Space>
  );
}
