import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { statusLabel } from '../utils/formatters';

const STATUS_COLOR = {
  COMPLETED:   '#16a34a',
  IN_PROGRESS: '#1769aa',
  NOT_STARTED: '#64748b',
  OVERDUE:     '#dc2626',
};

const STATUS_ORDER = ['COMPLETED', 'IN_PROGRESS', 'NOT_STARTED', 'OVERDUE'];

export default function KpiDonutChart({ data = {} }) {
  const rows = STATUS_ORDER
    .filter((key) => data[key] != null)
    .map((key) => ({
      key,
      name: statusLabel[key] || key,
      value: data[key],
      color: STATUS_COLOR[key],
    }));

  // Thêm các key không nằm trong STATUS_ORDER
  Object.entries(data).forEach(([key, value]) => {
    if (!STATUS_ORDER.includes(key)) {
      rows.push({ key, name: statusLabel[key] || key, value, color: '#a3a3a3' });
    }
  });

  const total = rows.reduce((sum, r) => sum + r.value, 0);

  return (
    <div className="donut-chart-wrap">
      <div className="donut-chart-main">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={rows}
              innerRadius={65}
              outerRadius={95}
              paddingAngle={2}
              dataKey="value"
              nameKey="name"
              startAngle={90}
              endAngle={-270}
            >
              {rows.map((entry) => (
                <Cell key={entry.key} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip formatter={(value, name) => [value, name]} />
          </PieChart>
        </ResponsiveContainer>

        {/* Tổng số ở giữa */}
        <div className="donut-chart-center">
          <span className="donut-chart-center__total">{total}</span>
          <span className="donut-chart-center__label">Tổng</span>
        </div>
      </div>

      {/* Legend bên ngoài */}
      <div className="donut-chart-legend">
        {rows.map((entry) => (
          <div key={entry.key} className="donut-chart-legend__item">
            <span className="donut-chart-legend__dot" style={{ background: entry.color }} />
            <span className="donut-chart-legend__name">{entry.name}</span>
            <span className="donut-chart-legend__value">{entry.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
