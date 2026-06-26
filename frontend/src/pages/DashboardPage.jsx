import { Card, Col, Row, Space, Typography } from 'antd';
import { CheckCircleOutlined, ClockCircleOutlined, TeamOutlined, TrophyOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { kpiApi } from '../api/kpiApi';
import KpiDonutChart from '../components/KpiDonutChart';
import KpiTrendChart from '../components/KpiTrendChart';
import StatCard from '../components/StatCard';
import { riskColor } from '../utils/formatters';

function KpiRankList({ users, type }) {
  if (!users?.length) return <div style={{ color: '#94a3b8', textAlign: 'center', padding: '24px 0' }}>Không có dữ liệu</div>;
  return (
    <div className="kpi-rank-list">
      {users.map((item, index) => (
        <div key={item.user_id} className="kpi-rank-item">
          <span className={`kpi-rank-item__index kpi-rank-item__index--${type}`}>
            {index + 1}
          </span>
          <div className="kpi-rank-item__info">
            <span className="kpi-rank-item__name">{item.full_name}</span>
            <span className="kpi-rank-item__dept">{item.department}</span>
          </div>
          <span className="kpi-rank-item__score" style={{ color: riskColor(item.score) }}>
            {item.score}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  useEffect(() => { kpiApi.dashboard().then(setData); }, []);
  const dashboard = data || { total_users: 38, avg_kpi: 82.6, task_completed: 158, task_total: 194, task_overdue: 12, task_status: {}, top_users: [], low_users: [] };

  return (
    <Space direction="vertical" size={18} className="page">
      <Typography.Title level={3}>Dashboard Tổng quan Lãnh đạo</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}><StatCard title="Tổng cán bộ" value={dashboard.total_users} icon={<TeamOutlined />} /></Col>
        <Col xs={24} md={6}><StatCard title="KPI trung bình" value={dashboard.avg_kpi} precision={1} suffix="/100" icon={<TrophyOutlined />} /></Col>
        <Col xs={24} md={6}><StatCard title="Nhiệm vụ hoàn thành" value={dashboard.task_completed} suffix={`/${dashboard.task_total}`} icon={<CheckCircleOutlined />} /></Col>
        <Col xs={24} md={6}><StatCard title="Nhiệm vụ quá hạn" value={dashboard.task_overdue} icon={<ClockCircleOutlined />} /></Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}><Card title="Trạng thái nhiệm vụ"><KpiDonutChart data={dashboard.task_status} /></Card></Col>
        <Col xs={24} lg={12}><Card title="Xu hướng KPI"><KpiTrendChart /></Card></Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Top 5 KPI cao nhất">
            <KpiRankList users={dashboard.top_users} type="top" />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Top 5 KPI thấp nhất">
            <KpiRankList users={dashboard.low_users} type="low" />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
