import { Button, Card, Descriptions, Progress, Space, Table, Typography, message, Spin } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { kpiApi } from '../api/kpiApi';
import { riskLevelLabel } from '../utils/formatters';

export default function KpiEvaluationPage() {
  const { userId } = useParams();
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);

  const load = () => {
    setLoading(true);
    kpiApi.score(userId)
      .then(setScore)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [userId]);

  const recompute = async () => {
    setComputing(true);
    try {
      const res = await kpiApi.recompute(userId);
      setScore(res);
      message.success('Rule Engine đã tính lại KPI');
    } catch (error) {
      message.error('Không tính lại được KPI');
    } finally {
      setComputing(false);
    }
  };

  const rows = score?.breakdown_json?.breakdown || [];
  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-title-row">
        <Typography.Title level={3}>AI Đánh giá KPI</Typography.Title>
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          loading={computing}
          onClick={recompute}
        >
          {computing ? 'Đang xử lý...' : 'Tính lại KPI'}
        </Button>
      </div>

      <Spin spinning={computing || loading} >
        <Space direction="vertical" size={18} style={{ width: '100%' }}>
          <Card>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="Điểm tổng">
                <Progress type="circle" percent={Math.round(score?.total_score || 0)} size="small" />
              </Descriptions.Item>
              <Descriptions.Item label="Xếp loại"><strong>{score?.classification}</strong></Descriptions.Item>
              <Descriptions.Item label="Mức rủi ro">{riskLevelLabel[score?.risk_level] || score?.risk_level}</Descriptions.Item>
              <Descriptions.Item label="Kỳ đánh giá">{score?.period_month}</Descriptions.Item>
              <Descriptions.Item label="AI Giải thích" span={2}>
                <div className="ai-markdown-container">
                  <ReactMarkdown>{score?.ai_explanation || ''}</ReactMarkdown>
                </div>
              </Descriptions.Item>
            </Descriptions>
          </Card>
          <Card title="Ma trận tính điểm KPI">
            <Table
              rowKey="group_name"
              dataSource={rows}
              pagination={false}
              bordered
              columns={[
                { title: 'Tiêu chí đánh giá', dataIndex: 'group_name', render: (text) => <strong>{text}</strong> },
                { title: 'Trọng số', dataIndex: 'max_score', width: 100, align: 'center' },
                {
                  title: 'Điểm quy đổi thực tế', dataIndex: 'score', width: 160, align: 'center', render: (val, record) => (
                    <Typography.Text type={val < record.max_score * 0.7 ? 'danger' : 'success'}>
                      {val} / {record.max_score}
                    </Typography.Text>
                  )
                },
                {
                  title: 'Lý do', dataIndex: 'reasons', render: (items) => (
                    <ul style={{ paddingLeft: 20, margin: 0 }}>
                      {items?.map((item, idx) => <li key={idx}>{item}</li>)}
                    </ul>
                  )
                },
              ]}
            />
          </Card>
        </Space>
      </Spin>
    </Space>
  );
}
