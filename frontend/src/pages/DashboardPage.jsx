import { Card, Col, Row, Space, Typography, Spin } from 'antd';
import { CheckCircleOutlined, ClockCircleOutlined, TeamOutlined, TrophyOutlined, UserOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { kpiApi } from '../api/kpiApi';
import KpiDonutChart from '../components/KpiDonutChart';
import KpiTrendChart from '../components/KpiTrendChart';
import StatCard from '../components/StatCard';
import { riskColor } from '../utils/formatters';

import { List } from 'antd';

function OrgWideDashboard({ dashboard }) {
  return (
    <Space direction="vertical" size={18} className="page" style={{ width: '100%' }}>
      <Typography.Title level={3}>Dashboard Tổng quan Toàn cơ quan</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}><StatCard title="Tổng cán bộ" value={dashboard.total_users} icon={<TeamOutlined />} /></Col>
        <Col xs={24} md={6}><StatCard title="KPI trung bình toàn Sở" value={dashboard.avg_kpi} precision={1} suffix="/100" icon={<TrophyOutlined />} /></Col>
        <Col xs={24} md={6}><StatCard title="Nhiệm vụ hoàn thành" value={dashboard.task_completed} suffix={`/${dashboard.task_total}`} icon={<CheckCircleOutlined />} /></Col>
        <Col xs={24} md={6}><StatCard title="Nhiệm vụ quá hạn" value={dashboard.task_overdue} icon={<ClockCircleOutlined />} /></Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}><Card title="Trạng thái nhiệm vụ"><KpiDonutChart data={dashboard.task_status} /></Card></Col>
        <Col xs={24} lg={12}><Card title="Xu hướng KPI Toàn cơ quan"><KpiTrendChart /></Card></Col>
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

function DepartmentDashboard({ dashboard }) {
  return (
    <Space direction="vertical" size={18} className="page" style={{ width: '100%' }}>
      <Typography.Title level={3}>
        Dashboard Tổng quan {dashboard.department_name ? `- ${dashboard.department_name}` : 'Phòng ban'}
      </Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}><StatCard title="Nhân sự phòng" value={dashboard.total_users} icon={<TeamOutlined />} /></Col>
        <Col xs={24} md={6}><StatCard title="KPI trung bình phòng" value={dashboard.avg_kpi} precision={1} suffix="/100" icon={<TrophyOutlined />} /></Col>
        <Col xs={24} md={6}><StatCard title="Nhiệm vụ hoàn thành" value={dashboard.task_completed} suffix={`/${dashboard.task_total}`} icon={<CheckCircleOutlined />} /></Col>
        <Col xs={24} md={6}><StatCard title="Nhiệm vụ quá hạn" value={dashboard.task_overdue} icon={<ClockCircleOutlined />} /></Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}><Card title="Trạng thái nhiệm vụ phòng"><KpiDonutChart data={dashboard.task_status} /></Card></Col>
        <Col xs={24} lg={12}><Card title="Xu hướng KPI Phòng"><KpiTrendChart /></Card></Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Top 5 xuất sắc trong phòng">
            <List dataSource={dashboard.top_users} renderItem={(item) => <List.Item><b>{item.full_name}</b><span>{item.score}</span></List.Item>} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Top 5 nguy cơ trong phòng">
            <List dataSource={dashboard.low_users} renderItem={(item) => <List.Item><b>{item.full_name}</b><span>{item.score}</span></List.Item>} />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}

function PersonalDashboard({ dashboard }) {
  return (
    <Space direction="vertical" size={18} className="page" style={{ width: '100%' }}>
      <Typography.Title level={3}>Dashboard Cá nhân</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}><StatCard title="Điểm KPI Cá nhân" value={dashboard.avg_kpi} precision={1} suffix="/100" icon={<UserOutlined />} /></Col>
        <Col xs={24} md={8}><StatCard title="Nhiệm vụ hoàn thành" value={dashboard.task_completed} suffix={`/${dashboard.task_total}`} icon={<CheckCircleOutlined />} /></Col>
        <Col xs={24} md={8}><StatCard title="Nhiệm vụ quá hạn" value={dashboard.task_overdue} icon={<ClockCircleOutlined />} /></Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}><Card title="Tiến độ công việc cá nhân"><KpiDonutChart data={dashboard.task_status} /></Card></Col>
        <Col xs={24} lg={12}><Card title="Xu hướng KPI Cá nhân"><KpiTrendChart /></Card></Col>
      </Row>
    </Space>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    kpiApi.dashboard().then((res) => {
      setData(res);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Spin size="large" tip="Đang tải dữ liệu Dashboard..." />
      </div>
    );
  }

  const dashboard = data || { scope: "org_wide", total_users: 0, avg_kpi: 0, task_completed: 0, task_total: 0, task_overdue: 0, task_status: {}, top_users: [], low_users: [] };

  if (dashboard.scope === "personal") {
    return <PersonalDashboard dashboard={dashboard} />;
  }
  if (dashboard.scope === "department") {
    return <DepartmentDashboard dashboard={dashboard} />;
  }

  return <OrgWideDashboard dashboard={dashboard} />;
}
