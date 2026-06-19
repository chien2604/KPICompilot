import { Table } from 'antd';
import StatusTag from './StatusTag';
import { formatDate } from '../utils/formatters';

export default function TaskTable({ data = [], loading = false }) {
  return (
    <Table
      rowKey="id"
      loading={loading}
      dataSource={data}
      pagination={{ pageSize: 10 }}
      columns={[
        { title: 'Nhiệm vụ', dataIndex: 'title' },
        { title: 'Trạng thái', dataIndex: 'status', width: 150, render: (value) => <StatusTag status={value} /> },
        { title: 'Loại VB', dataIndex: 'document_type', width: 90 },
        { title: 'Hạn xử lý', dataIndex: 'deadline', width: 130, render: formatDate },
        { title: 'Minh chứng', dataIndex: 'evidence_count', width: 110 },
      ]}
    />
  );
}
