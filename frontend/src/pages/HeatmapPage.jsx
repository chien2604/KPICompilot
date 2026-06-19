import { Card, Space, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { kpiApi } from '../api/kpiApi';
import OrgHeatmap from '../components/OrgHeatmap';

export default function HeatmapPage() {
  const [data, setData] = useState([]);
  useEffect(() => { kpiApi.heatmap().then(setData); }, []);
  return (
    <Space direction="vertical" size={18} className="page">
      <Typography.Title level={3}>Heatmap Tổ chức</Typography.Title>
      <Card>
        <OrgHeatmap data={data} />
      </Card>
    </Space>
  );
}
