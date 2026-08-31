import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Empty } from "antd";

/** Render KPI history returned by the backend without substituting demo values. */
export default function KpiTrendChart({ data = [] }) {
  if (!data.length) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="Chưa có dữ liệu KPI"
      />
    );
  }
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data}>
        <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
        <XAxis dataKey="month" />
        <YAxis domain={[50, 100]} />
        <Tooltip />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#d31a1a"
          fill="#ffe7a3"
          fillOpacity={0.38}
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
