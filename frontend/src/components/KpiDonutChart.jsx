import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { statusLabel } from '../utils/formatters';

const COLORS = ['#16a34a', '#1769aa', '#dc2626', '#64748b'];

export default function KpiDonutChart({ data = {} }) {
  const rows = Object.entries(data).map(([name, value]) => ({ name: statusLabel[name] || name, value }));
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie data={rows} innerRadius={58} outerRadius={84} paddingAngle={3} dataKey="value" nameKey="name">
            {rows.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
