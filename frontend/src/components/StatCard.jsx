import { Card, Statistic } from 'antd';

export default function StatCard({ title, value, suffix, precision, icon }) {
  return (
    <Card className="stat-card">
      <div className="stat-card__icon">{icon}</div>
      <Statistic title={title} value={value} suffix={suffix} precision={precision} />
    </Card>
  );
}
