import { Card } from 'antd';
import { riskColor } from '../utils/formatters';

export default function OrgHeatmap({ data = [] }) {
  return (
    <div className="heatmap-grid">
      {data.map((item) => (
        <Card key={item.department_id} className="heatmap-cell">
          <div className="heatmap-cell__bar" style={{ background: riskColor(item.avg_kpi) }} />
          <div className="heatmap-cell__name">{item.department}</div>
          <div className="heatmap-cell__score">{item.avg_kpi}</div>
          <div className="muted">{item.user_count} cán bộ</div>
        </Card>
      ))}
    </div>
  );
}
