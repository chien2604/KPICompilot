import { Card, Col, Row, Space, Typography } from 'antd';
import { TeamOutlined, TrophyOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { kpiApi } from '../api/kpiApi';
import { userApi } from '../api/userApi';
import OrgHeatmap from '../components/OrgHeatmap';
import { riskColor } from '../utils/formatters';

export default function HeatmapPage() {
  const [heatmapData, setHeatmapData] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [users, setUsers] = useState([]);
  const [ranking, setRanking] = useState([]);

  useEffect(() => {
    Promise.all([kpiApi.heatmap(), userApi.departments(), userApi.list(), kpiApi.ranking({ month: '2026-06' })]).then(([h, d, u, r]) => {
      setHeatmapData(h);
      setDepartments(d);
      setUsers(u);
      setRanking(r);
    });
  }, []);

  // Tổng hợp số liệu
  const totalStaff = users.length;
  const avgKpi = heatmapData.length
    ? Math.round((heatmapData.reduce((s, d) => s + d.avg_kpi, 0) / heatmapData.length) * 10) / 10
    : null;
  const kpiColor = avgKpi !== null ? riskColor(avgKpi) : '#94a3b8';

  // Số dept đạt từng mức
  const deptGood   = heatmapData.filter((d) => d.avg_kpi >= 85).length;
  const deptWarn   = heatmapData.filter((d) => d.avg_kpi >= 70 && d.avg_kpi < 85).length;
  const deptAlert  = heatmapData.filter((d) => d.avg_kpi < 70).length;

  return (
    <Space direction="vertical" size={18} className="page">
      <Typography.Title level={3}>Bản đồ nhiệt hiệu suất tổ chức</Typography.Title>

      <Card>
        <OrgHeatmap data={heatmapData} departments={departments} users={users} ranking={ranking} />
      </Card>

      {/* Summary bar */}
      <Row gutter={[16, 16]}>
        {/* Tổng nhân lực */}
        <Col xs={24} md={8}>
          <Card className="heatmap-summary-card">
            <div className="heatmap-summary-card__icon" style={{ background: '#e8f3fc', color: '#1769aa' }}>
              <TeamOutlined />
            </div>
            <div className="heatmap-summary-card__body">
              <div className="heatmap-summary-card__label">Tổng nhân lực</div>
              <div className="heatmap-summary-card__value" style={{ color: '#1769aa' }}>{totalStaff}</div>
              <div className="heatmap-summary-card__sub">{departments.length} đơn vị</div>
            </div>
          </Card>
        </Col>

        {/* KPI trung bình toàn cơ quan */}
        <Col xs={24} md={8}>
          <Card className="heatmap-summary-card">
            <div className="heatmap-summary-card__icon" style={{ background: kpiColor + '20', color: kpiColor }}>
              <TrophyOutlined />
            </div>
            <div className="heatmap-summary-card__body">
              <div className="heatmap-summary-card__label">KPI trung bình toàn cơ quan</div>
              <div className="heatmap-summary-card__value" style={{ color: kpiColor }}>
                {avgKpi !== null ? avgKpi : '—'}
                <span className="heatmap-summary-card__suffix">/100</span>
              </div>
              <div className="heatmap-summary-card__sub">Kỳ tháng 06/2026</div>
            </div>
          </Card>
        </Col>

        {/* Phân loại đơn vị theo màu */}
        <Col xs={24} md={8}>
          <Card className="heatmap-summary-card">
            <div className="heatmap-summary-card__icon" style={{ background: '#f0fdf4', color: '#16a34a' }}>
              <TrophyOutlined />
            </div>
            <div className="heatmap-summary-card__body">
              <div className="heatmap-summary-card__label">Phân loại đơn vị</div>
              <div className="heatmap-summary-dept-row">
                <span className="heatmap-summary-dept-dot" style={{ background: '#16a34a' }} />
                <span className="heatmap-summary-dept-text">Tốt (≥85)</span>
                <span className="heatmap-summary-dept-count" style={{ color: '#16a34a' }}>{deptGood}</span>
              </div>
              <div className="heatmap-summary-dept-row">
                <span className="heatmap-summary-dept-dot" style={{ background: '#f59e0b' }} />
                <span className="heatmap-summary-dept-text">Cần lưu ý (70–84)</span>
                <span className="heatmap-summary-dept-count" style={{ color: '#f59e0b' }}>{deptWarn}</span>
              </div>
              <div className="heatmap-summary-dept-row">
                <span className="heatmap-summary-dept-dot" style={{ background: '#dc2626' }} />
                <span className="heatmap-summary-dept-text">Báo động (&lt;70)</span>
                <span className="heatmap-summary-dept-count" style={{ color: '#dc2626' }}>{deptAlert}</span>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
