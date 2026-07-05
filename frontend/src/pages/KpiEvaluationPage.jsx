import {
  Avatar, Button, Card, Col, InputNumber, Row, Select,
  Space, Spin, Table, Tag, Tooltip, Typography, message,
} from 'antd';
import {
  BankOutlined,
  IdcardOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SaveOutlined,
  StarFilled,
  TrophyOutlined,
  UserOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { kpiApi } from '../api/kpiApi';
import { taskApi } from '../api/taskApi';
import { useAuth } from '../contexts/AuthContext';
import { authApi } from '../api/authApi';
import { riskColor, riskLevelLabel } from '../utils/formatters';

/* ─── ScoreCircle ──────────────────────────────────────── */
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

/* ─── Main Page ────────────────────────────────────────── */
export default function KpiEvaluationPage() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();

  const [score, setScore] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);

  // Phân quyền chấm
  const [assignable, setAssignable] = useState([]);   // danh sách người có thể chấm
  const [canScore, setCanScore] = useState(false); // user này có nằm trong danh sách không

  // Chấm điểm nhiệm vụ
  const [tasks, setTasks] = useState([]);
  const [loadingTasks, setLoadingTasks] = useState(false);
  const [draftScores, setDraftScores] = useState({});  // { taskId: số }
  const [saving, setSaving] = useState({});  // { taskId: bool }

  /* ── Load KPI ─────────────────────────────────────── */
  const load = () => {
    setLoading(true);
    Promise.all([kpiApi.score(userId), kpiApi.profile(userId)])
      .then(([s, p]) => { setScore(s); setProfile(p); })
      .finally(() => setLoading(false));
  };

  /* ── Load danh sách người có thể chấm ────────────── */
  useEffect(() => {
    authApi.assignableUsers()
      .then((list) => {
        setAssignable(list);
        setCanScore(list.some((u) => String(u.id) === String(userId)));
      })
      .catch(() => { setAssignable([]); setCanScore(false); });
  }, [userId]);

  /* ── Load nhiệm vụ khi có quyền chấm ────────────── */
  useEffect(() => {
    if (!canScore) { setTasks([]); return; }
    setLoadingTasks(true);
    taskApi.list({ assigned_user_id: userId })
      .then(setTasks)
      .catch(() => setTasks([]))
      .finally(() => setLoadingTasks(false));
  }, [canScore, userId]);

  useEffect(() => { load(); }, [userId]);

  /* ── Auto-recompute lần đầu ──────────────────────── */
  const computedUsers = useRef(new Set());
  useEffect(() => {
    if (!loading && score && !computedUsers.current.has(userId)) {
      computedUsers.current.add(userId);
      recompute();
    }
  }, [loading, score, userId]);

  /* ── Tính lại KPI ────────────────────────────────── */
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

  /* ── Lưu điểm 1 task ─────────────────────────────── */
  const handleSaveScore = async (taskId, score) => {
    setSaving((s) => ({ ...s, [taskId]: true }));
    try {
      await taskApi.scoreAssignment(taskId, Number(userId), score);
      message.success('Đã lưu điểm');
      setDraftScores((d) => { const n = { ...d }; delete n[taskId]; return n; });
      // Refresh tasks để hiện điểm mới
      taskApi.list({ assigned_user_id: userId }).then(setTasks);
    } catch {
      message.error('Lưu điểm thất bại');
    } finally {
      setSaving((s) => ({ ...s, [taskId]: false }));
    }
  };

  /* ── Dropdown chọn người (chỉ khi có quyền chấm) ── */
  const assignableOptions = assignable.map((u) => ({
    value: u.id,
    label: `${u.full_name} — ${u.position_title || ''}`,
  }));

  const user = profile?.user;
  const color = score ? riskColor(score.total_score) : '#94a3b8';
  const rows = score?.breakdown_json?.breakdown || [];

  /* ── Cột bảng chấm nhiệm vụ ─────────────────────── */
  const scoringColumns = [
    {
      title: 'Nhiệm vụ',
      dataIndex: 'title',
      render: (t, r) => (
        <div>
          <div style={{ fontWeight: 600 }}>{t}</div>
          <div style={{ fontSize: 12, color: '#64748b' }}>Nhóm {r.document_type} · Trọng số {r.weight}</div>
        </div>
      ),
    },
    {
      title: 'Trạng thái', dataIndex: 'status', width: 130,
      render: (s) => {
        const MAP = { COMPLETED: ['Hoàn thành', '#16a34a'], IN_PROGRESS: ['Đang thực hiện', '#f59e0b'], NOT_STARTED: ['Chưa bắt đầu', '#94a3b8'], OVERDUE: ['Quá hạn', '#dc2626'] };
        const [lbl, clr] = MAP[s] || ['—', '#94a3b8'];
        return <Tag style={{ borderRadius: 20, fontWeight: 600, borderColor: clr, color: clr, background: clr + '18' }}>{lbl}</Tag>;
      },
    },
    {
      title: 'Tự chấm', width: 85, align: 'center',
      render: (_, r) => {
        const a = r.assignees?.find((x) => String(x.user_id) === String(userId));
        return a?.self_score != null
          ? <span style={{ fontWeight: 700, color: '#0891b2' }}>{a.self_score}</span>
          : <span style={{ color: '#94a3b8' }}>—</span>;
      },
    },
    {
      title: 'Điểm lãnh đạo chấm', width: 175, align: 'center',
      render: (_, r) => {
        const a = r.assignees?.find((x) => String(x.user_id) === String(userId));
        const draft = draftScores[r.id];
        return (
          <Space>
            <InputNumber
              min={0} max={100} step={0.5} size="small"
              value={draft !== undefined ? draft : a?.leader_score}
              onChange={(val) => setDraftScores((d) => ({ ...d, [r.id]: val }))}
              style={{ width: 80 }}
              placeholder="—"
            />
            {draft !== undefined && (
              <Tooltip title="Lưu điểm">
                <Button
                  type="primary" size="small" icon={<SaveOutlined />}
                  loading={saving[r.id]}
                  onClick={() => handleSaveScore(r.id, draft)}
                />
              </Tooltip>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Điểm cuối', width: 90, align: 'center',
      render: (_, r) => {
        const a = r.assignees?.find((x) => String(x.user_id) === String(userId));
        if (a?.final_score == null) return <span style={{ color: '#94a3b8' }}>—</span>;
        const c = riskColor(a.final_score);
        return <span style={{ fontWeight: 700, color: c, fontSize: 16 }}>{Number(a.final_score).toFixed(1)}</span>;
      },
    },
  ];

  return (
    <Space direction="vertical" size={20} className="page">

      {/* ── Tiêu đề + chọn người chấm ─────────────── */}
      <div className="page-title-row">
        <Typography.Title level={3} style={{ margin: 0 }}>AI Đánh giá KPI</Typography.Title>

        <Space>
          {/* Dropdown chọn người nếu có quyền chấm người khác */}
          {assignable.length > 0 && (
            <Select
              id="kpi-scoring-user-select"
              showSearch
              allowClear
              placeholder="Chọn cán bộ để chấm..."
              style={{ width: 260 }}
              options={assignableOptions}
              optionFilterProp="label"
              value={assignable.some((u) => String(u.id) === String(userId)) ? Number(userId) : undefined}
              onChange={(val) => { if (val) navigate(`/kpi/${val}`); }}
              suffixIcon={<StarFilled style={{ color: '#f59e0b' }} />}
            />
          )}

          {canScore && (
            <Button type="primary" icon={<ReloadOutlined />} loading={computing} onClick={recompute}>
              {computing ? 'Đang xử lý...' : 'Tính lại KPI'}
            </Button>
          )}
          {!canScore && String(userId) !== String(currentUser?.user_id) && (
            <Tag color="orange" style={{ fontSize: 13, padding: '4px 12px' }}>
              Chỉ xem — không có quyền chấm điểm
            </Tag>
          )}
        </Space>
      </div>

      <Spin spinning={computing || loading}>
        <Space direction="vertical" size={20} style={{ width: '100%' }}>

          {/* ── Row 1: Thông tin cán bộ + Điểm KPI ─── */}
          <Row gutter={[20, 20]}>
            <Col xs={24} lg={14}>
              <Card style={{ height: '100%' }}>
                <div className="kpi-user-header">
                  <Avatar
                    size={72} src={user?.avatar_url} icon={<UserOutlined />}
                    style={{ background: '#e8f3fc', color: '#1769aa', fontSize: 32, flexShrink: 0 }}
                  />
                  <div>
                    <div className="kpi-user-name">{user?.full_name || '—'}</div>
                    <div className="kpi-user-position">{user?.position_title || '—'}</div>
                  </div>
                </div>
                <div className="kpi-info-list">
                  <InfoItem icon={<BankOutlined />} label="Đơn vị" value={user?.department} />
                  <InfoItem icon={<IdcardOutlined />} label="Chức vụ" value={user?.position_title} />
                  <InfoItem icon={<SafetyCertificateOutlined />} label="Kỳ đánh giá" value={score?.period_month} />
                </div>
              </Card>
            </Col>

            <Col xs={24} lg={10}>
              <Card style={{ height: '100%' }}>
                <div className="kpi-score-panel">
                  <ScoreCircle score={score} />
                  <div className="kpi-score-meta">
                    <Tag style={{ fontSize: 15, fontWeight: 700, padding: '6px 16px', borderRadius: 20, background: color + '20', borderColor: color, color }}>
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

          {/* ── Row 2: Bảng chấm điểm nhiệm vụ (chỉ khi có quyền) ── */}
          {canScore && (
            <Card
              title={
                <span>
                  <StarFilled style={{ color: '#f59e0b', marginRight: 8 }} />
                  Chấm điểm nhiệm vụ
                  <span style={{ fontWeight: 400, fontSize: 13, color: '#64748b', marginLeft: 8 }}>
                    — Nhập điểm lãnh đạo rồi nhấn <SaveOutlined /> để lưu, sau đó "Tính lại KPI"
                  </span>
                </span>
              }
              extra={
                <Button
                  size="small" type="primary" icon={<ReloadOutlined />}
                  loading={computing} onClick={recompute}
                >
                  Tính lại KPI
                </Button>
              }
            >
              <Spin spinning={loadingTasks}>
                <Table
                  rowKey="id"
                  dataSource={tasks}
                  columns={scoringColumns}
                  pagination={{ pageSize: 10, showSizeChanger: false }}
                  scroll={{ x: 650 }}
                  locale={{ emptyText: 'Cán bộ này chưa có nhiệm vụ nào' }}
                />
              </Spin>
            </Card>
          )}

          {/* ── Row 3: AI Giải thích ──────────────────── */}
          {score?.ai_explanation && (
            <Card title={<span style={{ fontSize: 16, fontWeight: 700 }}>Nhận xét & Giải thích</span>}>
              <div className="ai-markdown-container">
                <ReactMarkdown>{score.ai_explanation}</ReactMarkdown>
              </div>
            </Card>
          )}

          {/* ── Row 4: Ma trận điểm ──────────────────── */}
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
                    <span style={{ display: 'inline-block', background: color + '20', borderColor: color, border: `1.5px solid ${color}`, color, fontWeight: 700, fontSize: 15, padding: '4px 14px', borderRadius: 20 }}>
                      <TrophyOutlined style={{ marginRight: 6 }} />
                      {score?.classification}
                    </span>
                  </Table.Summary.Cell>
                </Table.Summary.Row>
              )}
              columns={[
                {
                  title: 'Tiêu chí đánh giá', dataIndex: 'group_name',
                  render: (text) => <span style={{ fontWeight: 700 }}>{text}</span>,
                },
                { title: 'Trọng số', dataIndex: 'max_score', width: 110, align: 'center', render: (val) => <span style={{ fontWeight: 600 }}>{val}</span> },
                {
                  title: 'Điểm thực tế', dataIndex: 'score', width: 150, align: 'center',
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
                  title: 'Lý do', dataIndex: 'reasons',
                  render: (items) => (
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                      {items?.map((item, idx) => (
                        <li key={idx} style={{ marginBottom: 4 }}>{item.replace(/^[\s•\-\*]+/, '').trim()}</li>
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
