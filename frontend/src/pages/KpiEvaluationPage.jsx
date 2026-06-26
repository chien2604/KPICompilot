import { Avatar, Button, Card, Col, Row, Space, Spin, Table, Tag, Typography, message } from 'antd';
import {
  BankOutlined,
  IdcardOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  TrophyOutlined,
  UserOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { kpiApi } from '../api/kpiApi';
import { riskColor, riskLevelLabel } from '../utils/formatters';

function ScoreCircle({ score }) {
  if (!score) return null;
  const color = riskColor(score.total_score);
  const r = 70;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(score.total_score / 100, 1);
  return (
    <div className="kpi-score-circle-wrap">
      <svg width="180" height="180" viewBox="0 0 180 180">
        <circle cx="90" cy="90" r={r} fill="none" stroke="#f1f5f9" strokeWidth="12" />
        <circle
          cx="90" cy="90" r={r}
          fill="none" stroke={color} strokeWidth="12"
          strokeDasharray={`${pct * circ} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 90 90)"
        />
      </svg>
      <div className="kpi-score-circle-center">
        <span className="kpi-score-circle-val" style={{ color }}>{score.total_score}</span>
        <span className="kpi-score-circle-sub">/100</span>
      </div>
    </div>
  );
}

function InfoItem({ icon, label, value }) {
  return (
    <div className="kpi-info-item">
      <span className="kpi-info-item__icon">{icon}</span>
      <span className="kpi-info-item__label">{label}</span>
      <span className="kpi-info-item__value">{value || '—'}</span>
    </div>
  );
}

export default function KpiEvaluationPage() {
  const { userId } = useParams();
  const [score, setScore]     = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading]   = useState(false);
  const [computing, setComputing] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([kpiApi.score(userId), kpiApi.profile(userId)])
      .then(([s, p]) => { setScore(s); setProfile(p); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [userId]);

  const recompute = async () => {
    setComputing(true);
    try {
      const res = await kpiApi.recompute(userId);
      setScore(res);
      message.success('Rule Engine đã tính lại KPI');
    } catch {
      message.error('Không tính lại được KPI');
    } finally {
      setComputing(false);
    }
  };

  const computedUsers = useRef(new Set());
  useEffect(() => {
    if (!loading && score && !computedUsers.current.has(userId)) {
      computedUsers.current.add(userId);
      recompute();
    }
  }, [loading, score, userId]);

  const user  = profile?.user;
  const color = score ? riskColor(score.total_score) : '#94a3b8';
  const rows  = score?.breakdown_json?.breakdown || [];

  return (
    <Space direction="vertical" size={20} className="page">
      <div className="page-title-row">
        <Typography.Title level={3}>AI Đánh giá KPI</Typography.Title>
        <Button type="primary" icon={<ReloadOutlined />} loading={computing} onClick={recompute}>
          {computing ? 'Đang xử lý...' : 'Tính lại KPI'}
        </Button>
      </div>

      <Spin spinning={computing || loading}>
        <Space direction="vertical" size={20} style={{ width: '100%' }}>

          {/* ── Row 1: Thông tin cán bộ + Điểm KPI ── */}
          <Row gutter={[20, 20]}>
            {/* Thông tin cán bộ */}
            <Col xs={24} lg={14}>
              <Card style={{ height: '100%' }}>
                <div className="kpi-user-header">
                  <Avatar
                    size={72}
                    src={user?.avatar_url}
                    icon={<UserOutlined />}
                    style={{ background: '#e8f3fc', color: '#1769aa', fontSize: 32, flexShrink: 0 }}
                  />
                  <div>
                    <div className="kpi-user-name">{user?.full_name || '—'}</div>
                    <div className="kpi-user-position">{user?.position_title || '—'}</div>
                  </div>
                </div>
                <div className="kpi-info-list">
                  <InfoItem icon={<BankOutlined />}               label="Đơn vị"    value={user?.department} />
                  <InfoItem icon={<IdcardOutlined />}             label="Chức vụ"   value={user?.position_title} />
                  <InfoItem icon={<SafetyCertificateOutlined />}  label="Kỳ đánh giá" value={score?.period_month} />
                </div>
              </Card>
            </Col>

            {/* Điểm KPI */}
            <Col xs={24} lg={10}>
              <Card style={{ height: '100%' }}>
                <div className="kpi-score-panel">
                  <ScoreCircle score={score} />
                  <div className="kpi-score-meta">
                    <Tag
                      style={{
                        fontSize: 15, fontWeight: 700,
                        padding: '6px 16px', borderRadius: 20,
                        background: color + '20', borderColor: color, color,
                      }}
                    >
                      <TrophyOutlined /> {score?.classification || '—'}
                    </Tag>
                    <div className="kpi-score-risk" style={{ color }}>
                      <WarningOutlined />
                      <span>Rủi ro: {riskLevelLabel[score?.risk_level] || score?.risk_level || '—'}</span>
                    </div>
                  </div>
                </div>
              </Card>
            </Col>
          </Row>

          {/* ── Row 2: AI Giải thích ── */}
          {score?.ai_explanation && (
            <Card
              title={<span style={{ fontSize: 16, fontWeight: 700 }}>Nhận xét & Giải thích</span>}
            >
              <div className="ai-markdown-container">
                <ReactMarkdown>{score.ai_explanation}</ReactMarkdown>
              </div>
            </Card>
          )}

          {/* ── Row 3: Ma trận điểm ── */}
          <Card title={<span style={{ fontSize: 16, fontWeight: 700 }}>Ma trận tính điểm KPI</span>}>
            <Table
              rowKey="group_name"
              dataSource={rows}
              pagination={false}
              bordered
              rowClassName={() => 'kpi-matrix-row'}
              summary={() => (
                <Table.Summary.Row className="kpi-matrix-summary-row">
                  <Table.Summary.Cell index={0}>
                    <span style={{ fontWeight: 800, fontSize: 16 }}>TỔNG ĐIỂM KPI</span>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={1} align="center">
                    <span style={{ fontWeight: 700 }}>100</span>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={2} align="center">
                    <span style={{ fontWeight: 800, fontSize: 20, color }}>
                      {score?.total_score}
                      <span style={{ fontSize: 13, color: '#94a3b8', fontWeight: 400 }}> / 100</span>
                    </span>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={3}>
                    <span style={{
                      display: 'inline-block',
                      background: '#fff',
                      border: '1.5px solid #e5e7eb',
                      color: 'rgba(0,0,0,0.88)',
                      fontWeight: 700,
                      fontSize: 15,
                      padding: '4px 14px',
                      borderRadius: 20,
                    }}>
                      <TrophyOutlined style={{ marginRight: 6, color: color }} />
                      {score?.classification}
                    </span>
                  </Table.Summary.Cell>
                </Table.Summary.Row>
              )}
              columns={[
                {
                  title: 'Tiêu chí đánh giá',
                  dataIndex: 'group_name',
                  render: (text) => <span style={{ fontWeight: 700 }}>{text}</span>,
                },
                {
                  title: 'Trọng số',
                  dataIndex: 'max_score',
                  width: 110,
                  align: 'center',
                  render: (val) => <span style={{ fontWeight: 600 }}>{val}</span>,
                },
                {
                  title: 'Điểm thực tế',
                  dataIndex: 'score',
                  width: 150,
                  align: 'center',
                  render: (val, record) => {
                    const c = riskColor((val / record.max_score) * 100);
                    return (
                      <span style={{ fontWeight: 700, color: c, fontSize: 18 }}>
                        {val}<span style={{ fontSize: 14, color: '#94a3b8', fontWeight: 400 }}> / {record.max_score}</span>
                      </span>
                    );
                  },
                },
                {
                  title: 'Lý do',
                  dataIndex: 'reasons',
                  render: (items) => (
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                      {items?.map((item, idx) => (
                        <li key={idx} style={{ marginBottom: 4 }}>
                          {item.replace(/^[\s•\-\*]+/, '').trim()}
                        </li>
                      ))}
                    </ul>
                  ),
                },
              ]}
            />
          </Card>

        </Space>
      </Spin>
    </Space>
  );
}
