import { Card, Col, Row, Space, Typography } from "antd";
import { TeamOutlined, TrophyOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import { kpiApi } from "../api/kpiApi";
import { userApi } from "../api/userApi";
import OrgHeatmap from "../components/OrgHeatmap";
import { riskColor } from "../utils/formatters";

/** Return the current reporting month in YYYY-MM format. */
function currentMonth() {
  return new Date().toISOString().slice(0, 7);
}

/** Render organization and unit KPI performance from live API data. */
export default function HeatmapPage() {
  const [heatmapData, setHeatmapData] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [users, setUsers] = useState([]);
  const [ranking, setRanking] = useState([]);

  useEffect(() => {
    Promise.all([
      kpiApi.heatmap(),
      userApi.departments(),
      userApi.list(),
      kpiApi.ranking({ month: currentMonth() }),
    ]).then(([h, d, u, r]) => {
      setHeatmapData(h);
      setDepartments(d);
      setUsers(u);
      setRanking(r);
    });
  }, []);

  // Tổng hợp số liệu
  const totalStaff = users.filter((user) => !user.is_admin).length;
  const scoredDepartments = heatmapData.filter((item) => item.avg_kpi != null);
  const avgKpi = scoredDepartments.length
    ? Math.round(
        (scoredDepartments.reduce((sum, item) => sum + item.avg_kpi, 0) /
          scoredDepartments.length) *
          10,
      ) / 10
    : null;
  const kpiColor = avgKpi !== null ? riskColor(avgKpi) : "#94a3b8";

  // Số dept đạt từng mức
  const deptGood = heatmapData.filter((d) => d.avg_kpi >= 85).length;
  const deptWarn = heatmapData.filter(
    (d) => d.avg_kpi >= 70 && d.avg_kpi < 85,
  ).length;
  const deptAlert = heatmapData.filter(
    (d) => d.avg_kpi != null && d.avg_kpi < 70,
  ).length;

  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-intro">
        <div>
          <Typography.Title level={3}>
            Heatmap hiệu suất tổ chức
          </Typography.Title>
          <Typography.Text>
            So sánh nhanh kết quả KPI theo đơn vị và từng cán bộ
          </Typography.Text>
        </div>
        <span className="page-intro__period">
          Kỳ đánh giá · {currentMonth()}
        </span>
      </div>

      <Card>
        <div className="heatmap-page-toolbar">
          <span className="heatmap-page-toolbar__label">
            Chú giải hiệu suất
          </span>
          <span className="heatmap-legend-item heatmap-legend-item--good">
            Tốt · từ 85
          </span>
          <span className="heatmap-legend-item heatmap-legend-item--warning">
            Cần lưu ý · 70–84
          </span>
          <span className="heatmap-legend-item heatmap-legend-item--danger">
            Cần cải thiện · dưới 70
          </span>
        </div>
        <OrgHeatmap
          data={heatmapData}
          departments={departments}
          users={users}
          ranking={ranking}
        />
      </Card>

      {/* Summary bar */}
      <Row gutter={[16, 16]} className="heatmap-summary-row">
        {/* Tổng nhân lực */}
        <Col xs={24} md={8}>
          <Card className="heatmap-summary-card">
            <div
              className="heatmap-summary-card__icon"
              style={{ background: "#e0f2fe", color: "#0ea5e9" }}
            >
              <TeamOutlined />
            </div>
            <div className="heatmap-summary-card__body">
              <div className="heatmap-summary-card__label">Tổng số cán bộ</div>
              <div
                className="heatmap-summary-card__value"
                style={{ color: "#0ea5e9" }}
              >
                {totalStaff}
              </div>
              <div className="heatmap-summary-card__sub">
                {
                  departments.filter(
                    (item) => item.unit_type !== "ORGANIZATION",
                  ).length
                }{" "}
                đơn vị
              </div>
            </div>
          </Card>
        </Col>

        {/* KPI trung bình toàn cơ quan */}
        <Col xs={24} md={8}>
          <Card className="heatmap-summary-card">
            <div
              className="heatmap-summary-card__icon"
              style={{ background: kpiColor + "20", color: kpiColor }}
            >
              <TrophyOutlined />
            </div>
            <div className="heatmap-summary-card__body">
              <div className="heatmap-summary-card__label">
                KPI trung bình toàn cơ quan
              </div>
              <div
                className="heatmap-summary-card__value"
                style={{ color: kpiColor }}
              >
                {avgKpi !== null ? avgKpi : "—"}
                <span className="heatmap-summary-card__suffix">/100</span>
              </div>
              <div className="heatmap-summary-card__sub">
                Kỳ tháng {currentMonth().split("-").reverse().join("/")}
              </div>
            </div>
          </Card>
        </Col>

        {/* Phân loại đơn vị theo màu */}
        <Col xs={24} md={8}>
          <Card className="heatmap-summary-card">
            <div
              className="heatmap-summary-card__icon"
              style={{ background: "#f0fdf4", color: "#16a34a" }}
            >
              <TrophyOutlined />
            </div>
            <div className="heatmap-summary-card__body">
              <div className="heatmap-summary-card__label">
                Phân loại đơn vị
              </div>
              <div className="heatmap-summary-dept-row">
                <span
                  className="heatmap-summary-dept-dot"
                  style={{ background: "#16a34a" }}
                />
                <span className="heatmap-summary-dept-text">Tốt (≥85)</span>
                <span
                  className="heatmap-summary-dept-count"
                  style={{ color: "#16a34a" }}
                >
                  {deptGood}
                </span>
              </div>
              <div className="heatmap-summary-dept-row">
                <span
                  className="heatmap-summary-dept-dot"
                  style={{ background: "#f59e0b" }}
                />
                <span className="heatmap-summary-dept-text">
                  Cần lưu ý (70–84)
                </span>
                <span
                  className="heatmap-summary-dept-count"
                  style={{ color: "#f59e0b" }}
                >
                  {deptWarn}
                </span>
              </div>
              <div className="heatmap-summary-dept-row">
                <span
                  className="heatmap-summary-dept-dot"
                  style={{ background: "#dc2626" }}
                />
                <span className="heatmap-summary-dept-text">
                  Báo động (&lt;70)
                </span>
                <span
                  className="heatmap-summary-dept-count"
                  style={{ color: "#dc2626" }}
                >
                  {deptAlert}
                </span>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
