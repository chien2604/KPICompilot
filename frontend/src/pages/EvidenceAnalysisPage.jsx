import { Breadcrumb, Button, Card, Descriptions, Progress, Space, Typography, List, Tag, Row, Col, Badge } from 'antd';
import { ReloadOutlined, CheckCircleFilled, CloseCircleFilled, HomeOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { evidenceApi } from '../api/evidenceApi';

const { Title, Text, Paragraph } = Typography;

export default function EvidenceAnalysisPage() {
  const { evidenceId } = useParams();
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

  const load = () => evidenceApi.analysis(evidenceId).then(setAnalysis);
  useEffect(() => {
    load();
  }, [evidenceId]);

  const analyze = async () => { 
    setAnalyzing(true);
    try {
      await evidenceApi.analyze(evidenceId); 
      await load(); 
    } finally {
      setAnalyzing(false);
    }
  };

  if (!analysis) return null;

  const score = Math.round(analysis.relevance_score || 0);
  const getScoreColor = (s) => {
    if (s >= 85) return '#10b981';
    if (s >= 65) return '#f59e0b';
    return '#ef4444';
  };
  const getScoreLabel = (s) => {
    if (s >= 90) return 'Xuất sắc';
    if (s >= 80) return 'Tốt';
    if (s >= 65) return 'Đạt yêu cầu';
    if (s >= 40) return 'Chưa đạt';
    return 'Không phù hợp';
  };

  const scoreColor = getScoreColor(score);

  return (
    <div className="page">
      <Breadcrumb style={{ marginBottom: 12 }} items={[
        { title: <Link to="/evidences"><HomeOutlined /> Minh chứng</Link> },
        { title: 'AI Phân tích Minh chứng' },
      ]} />
      <div className="page-title-row" style={{ marginBottom: 16 }}>
        <Title level={3}>AI Phân tích Minh chứng</Title>
        <Button icon={<ReloadOutlined />} onClick={analyze} type="primary" loading={analyzing}>
          {analyzing ? 'Đang phân tích...' : 'Phân tích lại'}
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        {/* LEFT PANEL: Input (Extracted Text) */}
        <Col xs={24} lg={8}>
          <Card title="Nội dung trích xuất (Input)" style={{ height: '100%' }}>
            <pre className="text-preview" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 13, maxHeight: '75vh', overflowY: 'auto' }}>
              {analysis.extracted_text || 'Chưa có nội dung'}
            </pre>
          </Card>
        </Col>

        {/* RIGHT PANEL: Output (AI Results) */}
        <Col xs={24} lg={16}>
          <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
            
            {/* Score & Summary Card */}
            <Card>
              <Row gutter={24} align="middle">
                <Col>
                  <Progress
                    type="circle"
                    percent={score}
                    strokeColor={scoreColor}
                    format={(percent) => (
                      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1 }}>
                        <span style={{ fontSize: 28, fontWeight: 800, color: scoreColor }}>{percent}</span>
                        <span style={{ fontSize: 11, color: '#888' }}>/ 100</span>
                      </div>
                    )}
                    size={110}
                  />
                  <div style={{ textAlign: 'center', marginTop: 8 }}>
                    <Tag color={scoreColor} style={{ fontWeight: 600, border: 'none', borderRadius: 12 }}>
                      {getScoreLabel(score)}
                    </Tag>
                  </div>
                </Col>
                <Col flex="auto">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                    <Title level={4} style={{ margin: 0 }}>Kết quả đánh giá</Title>
                    <Badge status={analysis.status === 'ANALYZED' ? 'success' : 'processing'} text={analysis.status} />
                  </div>
                  
                  <div style={{ background: 'rgba(99,102,241,0.05)', padding: 16, borderRadius: 8, border: '1px solid rgba(99,102,241,0.2)' }}>
                    <div style={{ display: 'inline-block', background: 'linear-gradient(135deg,#6366f1,#06b6d4)', color: '#fff', fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 12, marginBottom: 8 }}>
                      ✦ NHẬN XÉT AI
                    </div>
                    <Paragraph style={{ margin: 0, color: '#475569', fontSize: 14 }}>
                      {analysis.summary || 'Không có nhận xét'}
                    </Paragraph>
                  </div>
                </Col>
              </Row>
            </Card>

            {/* Checklist and Strengths/Weaknesses Row */}
            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <Card title="Checklist kiểm tra" style={{ height: '100%' }} bodyStyle={{ padding: 12 }}>
                  <List
                    size="small"
                    dataSource={analysis.checklist || []}
                    renderItem={item => (
                      <List.Item style={{ padding: '8px 12px', background: 'rgba(0,0,0,0.02)', borderRadius: 8, marginBottom: 8, border: 'none' }}>
                        <Space align="start" style={{ width: '100%' }}>
                          {item.met ? <CheckCircleFilled style={{ color: '#10b981', marginTop: 4 }} /> : <CloseCircleFilled style={{ color: '#ef4444', marginTop: 4 }} />}
                          <div style={{ flex: 1 }}>
                            <Text strong={!item.met} style={{ fontSize: 13 }}>{item.item}</Text>
                            {item.note && (
                              <div style={{ color: '#64748b', fontSize: 12, marginTop: 4 }}>
                                {item.note} {!item.met && <Text type="danger">(Trừ {item.deduction}đ)</Text>}
                              </div>
                            )}
                          </div>
                        </Space>
                      </List.Item>
                    )}
                    locale={{ emptyText: 'Không có tiêu chí kiểm tra' }}
                  />
                </Card>
              </Col>
              
              <Col xs={24} md={12}>
                <Card title="Điểm mạnh & Cần cải thiện" style={{ height: '100%' }}>
                  <div style={{ marginBottom: 16 }}>
                    <Text strong style={{ color: '#10b981', textTransform: 'uppercase', fontSize: 12 }}>Điểm mạnh</Text>
                    <List
                      size="small"
                      dataSource={analysis.strengths || []}
                      renderItem={item => <List.Item style={{ border: 'none', padding: '4px 0', color: '#475569', fontSize: 13 }}><span style={{ color: '#10b981', marginRight: 8 }}>●</span> {item}</List.Item>}
                      locale={{ emptyText: 'Không có điểm mạnh nổi bật' }}
                    />
                  </div>
                  <div style={{ borderTop: '1px solid #f0f0f0', margin: '12px 0' }} />
                  <div>
                    <Text strong style={{ color: '#f59e0b', textTransform: 'uppercase', fontSize: 12 }}>Cần cải thiện</Text>
                    <List
                      size="small"
                      dataSource={analysis.weaknesses || []}
                      renderItem={item => <List.Item style={{ border: 'none', padding: '4px 0', color: '#475569', fontSize: 13 }}><span style={{ color: '#f59e0b', marginRight: 8 }}>●</span> {item}</List.Item>}
                      locale={{ emptyText: 'Không có điểm cần cải thiện' }}
                    />
                  </div>
                </Card>
              </Col>
            </Row>

          </Space>
        </Col>
      </Row>
    </div>
  );
}
