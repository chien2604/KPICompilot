import { Button, Progress, Table } from 'antd';
import { Link } from 'react-router-dom';
import StatusTag from './StatusTag';
import { formatDate } from '../utils/formatters';

export default function EvidenceTable({ data = [], loading = false }) {
  return (
    <Table
      rowKey="id"
      loading={loading}
      dataSource={data}
      pagination={{ pageSize: 10 }}
      columns={[
        { title: 'File', dataIndex: 'file_name' },
        { title: 'Task', dataIndex: 'task_id', width: 90 },
        { title: 'Trạng thái', dataIndex: 'status', width: 130, render: (value) => <StatusTag status={value} /> },
        { title: 'Phù hợp', dataIndex: 'ai_relevance_score', width: 130, render: (value) => <Progress percent={Math.round(value || 0)} size="small" /> },
        { title: 'Ngày tạo', dataIndex: 'created_at', width: 130, render: formatDate },
        { title: '', width: 120, render: (_, row) => <Link to={`/evidences/${row.id}/analysis`}><Button type="link">Phân tích</Button></Link> },
      ]}
    />
  );
}
