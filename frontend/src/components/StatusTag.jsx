import { Tag } from 'antd';
import { statusLabel } from '../utils/formatters';

const colors = {
  COMPLETED: 'success',
  IN_PROGRESS: 'processing',
  OVERDUE: 'error',
  NOT_STARTED: 'default',
  UPLOADED: 'default',
  PROCESSING: 'processing',
  ANALYZED: 'success',
  FAILED: 'error',
};

export default function StatusTag({ status }) {
  return <Tag color={colors[status] || 'default'}>{statusLabel[status] || status}</Tag>;
}
