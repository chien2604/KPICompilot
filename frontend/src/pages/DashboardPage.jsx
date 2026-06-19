import { Card, Col, List, Row, Space, Typography } from 'antd';
import { CheckCircleOutlined, ClockCircleOutlined, TeamOutlined, TrophyOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { kpiApi } from '../api/kpiApi';
import KpiDonutChart from '../components/KpiDonutChart';
import KpiTrendChart from '../components/KpiTrendChart';
import StatCard from '../components/StatCard';

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
        <Col xs={24} md={6}><StatCard title="Nhiệm vụ hoàn thành" value={`${dashboard.task_completed}/${dashboard.task_total}`} icon={<CheckCircleOutlined />} /></Col>
        <Col xs={24} md={6}><StatCard title="Nhiệm vụ quá hạn" value={dashboard.task_overdue} icon={<ClockCircleOutlined />} /></Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}><Card title="Trạng thái nhiệm vụ"><KpiDonutChart data={dashboard.task_status} /></Card></Col>
        <Col xs={24} lg={12}><Card title="Xu hướng KPI"><KpiTrendChart /></Card></Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Top 5 KPI cao nhất">
            <List dataSource={dashboard.top_users} renderItem={(item) => <List.Item><b>{item.full_name}</b><span>{item.score}</span></List.Item>} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Top 5 KPI thấp nhất">
            <List dataSource={dashboard.low_users} renderItem={(item) => <List.Item><b>{item.full_name}</b><span>{item.score}</span></List.Item>} />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
