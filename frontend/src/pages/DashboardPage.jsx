import { Card, Col, Empty, List, Row, Space, Typography, Spin } from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  TrophyOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useEffect, useState } from "react";
import { kpiApi } from "../api/kpiApi";
import { userApi } from "../api/userApi";
import KpiDonutChart from "../components/KpiDonutChart";
import KpiTrendChart from "../components/KpiTrendChart";
import StatCard from "../components/StatCard";
import OrgHeatmap from "../components/OrgHeatmap";

/** Render organization-wide metrics for administrators. */
function OrganizationDashboard({ dashboard, organization }) {
  return (
    <Space
      direction="vertical"
      size={18}
      className="page"
      style={{ width: "100%" }}
    >
      <div className="page-intro">
        <div>
          <Typography.Title level={3}>
            Tổng quan UBND xã Nghĩa Lâm
          </Typography.Title>
          <Typography.Text>
            Theo dõi kỷ cương, tiến độ công việc và chất lượng phục vụ người dân
          </Typography.Text>
        </div>
        <span className="page-intro__period">Kỳ đánh giá · Tháng hiện tại</span>
      </div>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}>
          <StatCard
            title="Tổng cán bộ"
            value={dashboard.total_users}
            icon={<TeamOutlined />}
            subtext={`${organization.departments.filter((item) => ["LEADERSHIP", "UNIT"].includes(item.unit_type)).length} đơn vị trực thuộc`}
            tone="red"
          />
        </Col>
        <Col xs={24} md={6}>
          <StatCard
            title="KPI trung bình"
            value={dashboard.avg_kpi ?? 0}
            precision={1}
            suffix="/100"
            icon={<TrophyOutlined />}
            subtext={`${dashboard.kpi_eligible_users} người thuộc phạm vi KPI`}
            tone="green"
          />
        </Col>
        <Col xs={24} md={6}>
          <StatCard
            title="Nhiệm vụ hoàn thành"
            value={dashboard.task_completed}
            suffix={`/${dashboard.task_total}`}
            icon={<CheckCircleOutlined />}
            subtext={
              dashboard.task_total
                ? `${Math.round((dashboard.task_completed / dashboard.task_total) * 100)}% tổng nhiệm vụ`
                : "Chưa có nhiệm vụ"
            }
            tone="blue"
          />
        </Col>
        <Col xs={24} md={6}>
          <StatCard
            title="Nhiệm vụ quá hạn"
            value={dashboard.task_overdue}
            icon={<ClockCircleOutlined />}
            subtext="Cần ưu tiên xử lý"
            tone="orange"
          />
        </Col>
      </Row>
      <div className="gov-motto-banner">
        <span className="gov-motto-banner__seal">★</span>
        <div>
          <strong>KỶ CƯƠNG · TRÁCH NHIỆM · HIỆU QUẢ · PHỤC VỤ NHÂN DÂN</strong>
          <span>
            Xây dựng Nghĩa Lâm phát triển bền vững, văn minh, giàu bản sắc
          </span>
        </div>
      </div>
      <Card
        className="organization-card"
        title="Cơ cấu cán bộ, công chức, viên chức"
        extra={`${dashboard.kpi_eligible_users}/${dashboard.total_users} người thuộc phạm vi KPI`}
      >
        <OrgHeatmap {...organization} compact />
      </Card>
      <Row gutter={[16, 16]} className="dashboard-equal-row">
        <Col xs={24} lg={12}>
          <Card title="Trạng thái nhiệm vụ" className="dashboard-chart-card">
            <KpiDonutChart data={dashboard.task_status} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title="Xu hướng KPI toàn tổ chức"
            className="dashboard-chart-card"
          >
            <KpiTrendChart data={dashboard.kpi_trend} />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} className="dashboard-equal-row">
        <Col xs={24} lg={12}>
          <Card title="Top 5 KPI cao nhất">
            <List
              dataSource={dashboard.top_users}
              renderItem={(item) => (
                <List.Item>
                  <b>{item.full_name}</b>
                  <span>{item.score}</span>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Top 5 KPI thấp nhất">
            <List
              dataSource={dashboard.low_users}
              renderItem={(item) => (
                <List.Item>
                  <b>{item.full_name}</b>
                  <span>{item.score}</span>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}

/** Render unit metrics for organization and unit leaders. */
function DepartmentDashboard({ dashboard }) {
  return (
    <Space
      direction="vertical"
      size={18}
      className="page"
      style={{ width: "100%" }}
    >
      <Typography.Title level={3}>
        Tổng quan {dashboard.department_name || "đơn vị"}
      </Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}>
          <StatCard
            title="Nhân sự đơn vị"
            value={dashboard.total_users}
            icon={<TeamOutlined />}
          />
        </Col>
        <Col xs={24} md={6}>
          <StatCard
            title="KPI trung bình đơn vị"
            value={dashboard.avg_kpi ?? 0}
            precision={1}
            suffix="/100"
            icon={<TrophyOutlined />}
          />
        </Col>
        <Col xs={24} md={6}>
          <StatCard
            title="Nhiệm vụ hoàn thành"
            value={dashboard.task_completed}
            suffix={`/${dashboard.task_total}`}
            icon={<CheckCircleOutlined />}
          />
        </Col>
        <Col xs={24} md={6}>
          <StatCard
            title="Nhiệm vụ quá hạn"
            value={dashboard.task_overdue}
            icon={<ClockCircleOutlined />}
          />
        </Col>
      </Row>
      <Row gutter={[16, 16]} className="dashboard-equal-row">
        <Col xs={24} lg={12}>
          <Card
            title="Trạng thái nhiệm vụ đơn vị"
            className="dashboard-chart-card"
          >
            <KpiDonutChart data={dashboard.task_status} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Xu hướng KPI đơn vị" className="dashboard-chart-card">
            <KpiTrendChart data={dashboard.kpi_trend} />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} className="dashboard-equal-row">
        <Col xs={24} lg={12}>
          <Card title="Top 5 KPI cao nhất trong đơn vị">
            <List
              dataSource={dashboard.top_users}
              renderItem={(item) => (
                <List.Item>
                  <b>{item.full_name}</b>
                  <span>{item.score}</span>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Top 5 KPI thấp nhất trong đơn vị">
            <List
              dataSource={dashboard.low_users}
              renderItem={(item) => (
                <List.Item>
                  <b>{item.full_name}</b>
                  <span>{item.score}</span>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}

/** Render personal task and KPI metrics for a member. */
function PersonalDashboard({ dashboard }) {
  return (
    <Space
      direction="vertical"
      size={18}
      className="page"
      style={{ width: "100%" }}
    >
      <Typography.Title level={3}>Dashboard Cá nhân</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <StatCard
            title="Điểm KPI Cá nhân"
            value={dashboard.avg_kpi}
            precision={1}
            suffix="/100"
            icon={<UserOutlined />}
          />
        </Col>
        <Col xs={24} md={8}>
          <StatCard
            title="Nhiệm vụ hoàn thành"
            value={dashboard.task_completed}
            suffix={`/${dashboard.task_total}`}
            icon={<CheckCircleOutlined />}
          />
        </Col>
        <Col xs={24} md={8}>
          <StatCard
            title="Nhiệm vụ quá hạn"
            value={dashboard.task_overdue}
            icon={<ClockCircleOutlined />}
          />
        </Col>
      </Row>
      <Row gutter={[16, 16]} className="dashboard-equal-row">
        <Col xs={24} lg={12}>
          <Card
            title="Tiến độ công việc cá nhân"
            className="dashboard-chart-card"
          >
            <KpiDonutChart data={dashboard.task_status} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Xu hướng KPI cá nhân" className="dashboard-chart-card">
            <KpiTrendChart data={dashboard.kpi_trend} />
          </Card>
        </Col>
      </Row>
    </Space>
  );
}

/** Load and render the dashboard authorized for the current account. */
export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [organization, setOrganization] = useState({
    data: [],
    departments: [],
    users: [],
    ranking: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      kpiApi.dashboard(),
      kpiApi.heatmap(),
      userApi.departments(),
      userApi.list(),
      kpiApi.ranking({}).catch(() => []),
    ])
      .then(([dashboard, heatmap, departments, users, ranking]) => {
        setData(dashboard);
        setOrganization({ data: heatmap, departments, users, ranking });
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "60vh",
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return <Empty description="Không thể tải dữ liệu dashboard" />;
  }

  const dashboard = data;

  if (dashboard.scope === "personal") {
    return <PersonalDashboard dashboard={dashboard} />;
  }
  if (dashboard.scope === "department") {
    return <DepartmentDashboard dashboard={dashboard} />;
  }

  return (
    <OrganizationDashboard dashboard={dashboard} organization={organization} />
  );
}
