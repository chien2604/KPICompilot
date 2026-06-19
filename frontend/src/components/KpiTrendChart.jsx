import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const demo = [
  { month: '02', value: 78 },
  { month: '03', value: 80 },
  { month: '04', value: 81 },
  { month: '05', value: 82 },
  { month: '06', value: 82.6 },
];

export default function KpiTrendChart({ data = demo }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" />
        <YAxis domain={[50, 100]} />
        <Tooltip />
        <Area type="monotone" dataKey="value" stroke="#1769aa" fill="#d7ebfb" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
