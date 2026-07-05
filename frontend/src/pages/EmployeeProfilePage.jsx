import { Avatar, Card, Col, DatePicker, Empty, Row, Space, Tag, Typography } from 'antd';
import {
  BankOutlined,
  IdcardOutlined,
  MailOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { useParams } from 'react-router-dom';
import { kpiApi } from '../api/kpiApi';
import TaskTable from '../components/TaskTable';
import { kpiTemplateLabel, riskColor, riskLevelLabel, roleLabel } from '../utils/formatters';

function InfoRow({ icon, label, value }) {
  return (
    <div className="profile-info-row">
      <span className="profile-info-row__icon">{icon}</span>
      <span className="profile-info-row__label">{label}</span>
      <span className="profile-info-row__value">{value || '—'}</span>
    </div>
  );
}

function KpiScoreCard({ score }) {
  if (!score) return (
    <div className="profile-kpi-empty">Chưa có dữ liệu KPI</div>
  );

  const color = riskColor(score.total_score);
  const pct = Math.min(score.total_score / 100, 1);
  const r = 80;
  const circ = 2 * Math.PI * r;

  return (
    <div className="profile-kpi-card">
      {/* Vòng tròn điểm */}
      <div className="profile-kpi-circle-wrap">
        <svg width="220" height="220" viewBox="0 0 220 220">
          <circle cx="110" cy="110" r={r} fill="none" stroke="#f1f5f9" strokeWidth="14" />
          <circle
            cx="110" cy="110" r={r}
            fill="none"
            stroke={color}
            strokeWidth="14"
            strokeDasharray={`${pct * circ} ${circ}`}
            strokeLinecap="round"
            transform="rotate(-90 110 110)"
          />
        </svg>
        <div className="profile-kpi-circle-center">
          <span className="profile-kpi-score" style={{ color }}>{score.total_score}</span>
          <span className="profile-kpi-score-label">/100</span>
        </div>
      </div>

      {/* Xếp loại + rủi ro */}
      <div className="profile-kpi-meta">
        <Tag color={color} style={{ fontSize: 14, padding: '4px 12px', borderRadius: 8 }}>
          {score.classification}
        </Tag>
        <div className="profile-kpi-risk" style={{ color }}>
          <WarningOutlined />
          <span>Rủi ro: {riskLevelLabel[score.risk_level] || score.risk_level}</span>
        </div>
      </div>
    </div>
  );
}

export default function EmployeeProfilePage() {
  const { userId } = useParams();
  const [profile, setProfile] = useState(null);
  const [score, setScore] = useState(null);
  const [taskFilter, setTaskFilter] = useState(null);
  const [selectedMonth, setSelectedMonth] = useState(dayjs('2026-06', 'YYYY-MM'));

  useEffect(() => { kpiApi.profile(userId).then(setProfile); }, [userId]);

  useEffect(() => {
    const month = selectedMonth.format('YYYY-MM');
    kpiApi.score(userId, month).then(setScore).catch(() => setScore(null));
  }, [userId, selectedMonth]);

  const tasks = profile?.tasks;

  const filteredTasks = useMemo(() =>
    taskFilter ? (tasks || []).filter((t) => t.status === taskFilter) : (tasks || []),
    [tasks, taskFilter]
  );

  const FILTER_OPTIONS = [
    { value: null,          label: 'Tất cả',          color: '#0062ff' },
    { value: 'COMPLETED',   label: 'Hoàn thành',      color: '#16a34a' },
    { value: 'IN_PROGRESS', label: 'Đang thực hiện',  color: '#f59e0b' },
    { value: 'NOT_STARTED', label: 'Chưa bắt đầu',   color: '#64748b' },
    { value: 'OVERDUE',     label: 'Quá hạn',         color: '#dc2626' },
  ];

  if (!profile) return <Empty description="Đang tải hồ sơ" />;

  const { user } = profile;

  // Thống kê tác nghiệp từ tasks
  const taskStats = {
    total: tasks?.length || 0,
    COMPLETED:   tasks?.filter(t => t.status === 'COMPLETED').length   || 0,
    IN_PROGRESS: tasks?.filter(t => t.status === 'IN_PROGRESS').length || 0,
    NOT_STARTED: tasks?.filter(t => t.status === 'NOT_STARTED').length || 0,
    OVERDUE:     tasks?.filter(t => t.status === 'OVERDUE').length     || 0,
  };

  const TASK_ITEMS = [
    { label: 'Tổng nhiệm vụ',    value: taskStats.total,       color: '#0062ff', bg: '#e6f0ff' },
    { label: 'Hoàn thành',       value: taskStats.COMPLETED,   color: '#16a34a', bg: '#dcfce7' },
    { label: 'Đang thực hiện',   value: taskStats.IN_PROGRESS, color: '#f59e0b', bg: '#fef9c3' },
    { label: 'Chưa bắt đầu',     value: taskStats.NOT_STARTED, color: '#64748b', bg: '#f1f5f9' },
    { label: 'Quá hạn',          value: taskStats.OVERDUE,     color: '#dc2626', bg: '#fee2e2' },
  ];

  return (
    <Space direction="vertical" size={20} className="page">
      <Typography.Title level={3}>Hồ sơ Cán bộ</Typography.Title>

      <Row gutter={[20, 20]}>
        {/* Cột trái: Avatar + Thông tin chi tiết */}
        <Col xs={24} lg={12}>
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {/* Avatar card */}
            <Card className="profile-avatar-card">
              <div className="profile-avatar-wrap">
                <Avatar
                  size={96}
                  src={user.avatar_url}
                  icon={<UserOutlined />}
                  style={{ background: '#e6f0ff', color: '#0062ff', fontSize: 40 }}
                />
                <div className="profile-avatar-info">
                  <div className="profile-avatar-name">{user.full_name}</div>
                  <div className="profile-avatar-position">{user.position_title}</div>
                  <Tag color="blue" style={{ marginTop: 6, fontSize: 13 }}>
                    {roleLabel[user.role] || user.role}
                  </Tag>
                </div>
              </div>
            </Card>

            {/* Thông tin cán bộ */}
            <Card title={<span style={{ fontSize: 16, fontWeight: 700 }}>Thông tin cán bộ</span>}>
              <div className="profile-info-list">
                <InfoRow icon={<MailOutlined />}      label="Email"       value={user.email} />
                <InfoRow icon={<BankOutlined />}      label="Đơn vị"      value={user.department} />
                <InfoRow icon={<IdcardOutlined />}    label="Chức vụ"     value={user.position_title} />
                <InfoRow icon={<UserOutlined />}      label="Vai trò"     value={roleLabel[user.role] || user.role} />
                <InfoRow
                  icon={<SafetyCertificateOutlined />}
                  label="Mẫu KPI"
                  value={kpiTemplateLabel[user.kpi_role_template] || user.kpi_role_template}
                />
              </div>
            </Card>
          </Space>
        </Col>

        {/* Cột phải: Chỉ Điểm KPI */}
        <Col xs={24} lg={12}>
          <Card
            title={<span style={{ fontSize: 16, fontWeight: 700 }}>Điểm KPI</span>}
            extra={
              <DatePicker
                picker="month"
                value={selectedMonth}
                onChange={(val) => val && setSelectedMonth(val)}
                format="MM/YYYY"
                allowClear={false}
                style={{ width: 130 }}
              />
            }
            style={{ height: '100%' }}
          >
            <KpiScoreCard score={score} />
          </Card>
        </Col>
      </Row>

      {/* Thống kê tác nghiệp */}
      <Card title={<span style={{ fontSize: 16, fontWeight: 700 }}>Thống kê tác nghiệp</span>}>
        <div className="task-stats-row">
          {TASK_ITEMS.map((item) => (
            <div key={item.label} className="task-stats-item" style={{ background: item.bg }}>
              <div className="task-stats-item__value" style={{ color: item.color }}>{item.value}</div>
              <div className="task-stats-item__label" style={{ color: item.color }}>{item.label}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Bảng nhiệm vụ */}
      <Card title={<span style={{ fontSize: 16, fontWeight: 700 }}>Nhiệm vụ liên quan</span>}>
        <div className="task-filter-bar__inner" style={{ marginBottom: 14 }}>
          {FILTER_OPTIONS.map((opt) => (
            <Tag
              key={opt.value ?? 'all'}
              style={{
                borderColor: opt.color,
                color: taskFilter === opt.value ? '#fff' : opt.color,
                background: taskFilter === opt.value ? opt.color : `${opt.color}15`,
                cursor: 'pointer',
                fontSize: 14,
                padding: '4px 14px',
                borderRadius: 20,
                userSelect: 'none',
              }}
              onClick={() => setTaskFilter(opt.value)}
            >
              {opt.label}
              {taskFilter === opt.value && opt.value !== null && ' ✕'}
            </Tag>
          ))}
          {taskFilter && (
            <span style={{ fontSize: 13, color: '#94a3b8' }}>
              {filteredTasks.length} / {tasks?.length || 0} nhiệm vụ
            </span>
          )}
        </div>
        <TaskTable data={filteredTasks} />
      </Card>
    </Space>
  );
}
