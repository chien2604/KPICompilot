import { Button, Card, Descriptions, Progress, Space, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { evidenceApi } from '../api/evidenceApi';

export default function EvidenceAnalysisPage() {
  const { evidenceId } = useParams();
  const [analysis, setAnalysis] = useState(null);
  const load = () => evidenceApi.analysis(evidenceId).then(setAnalysis);
  useEffect(() => {
    load();
  }, [evidenceId]);
  const analyze = async () => { await evidenceApi.analyze(evidenceId); load(); };

  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-title-row">
        <Typography.Title level={3}>AI Phân tích Minh chứng</Typography.Title>
        <Button icon={<ReloadOutlined />} onClick={analyze}>Phân tích lại</Button>
      </div>
      <Card>
        <Descriptions column={1}>
          <Descriptions.Item label="Trạng thái">{analysis?.status}</Descriptions.Item>
          <Descriptions.Item label="Độ phù hợp"><Progress percent={Math.round(analysis?.relevance_score || 0)} /></Descriptions.Item>
          <Descriptions.Item label="Tóm tắt">{analysis?.summary}</Descriptions.Item>
          <Descriptions.Item label="Thiếu sót">{(analysis?.missing_points || []).join(', ') || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card title="Text trích xuất">
        <pre className="text-preview">{analysis?.extracted_text || 'Chưa có nội dung'}</pre>
      </Card>
    </Space>
  );
}
