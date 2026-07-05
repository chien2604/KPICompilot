import { Tag } from 'antd';
import { statusLabel } from '../utils/formatters';

const colors = {
  COMPLETED: 'cyan',
  IN_PROGRESS: 'blue',
  OVERDUE: 'geekblue',
  NOT_STARTED: 'default',
  UPLOADED: 'default',
  PROCESSING: 'blue',
  ANALYZED: 'cyan',
  FAILED: 'geekblue',
};

export default function StatusTag({ status }) {
  return <Tag color={colors[status] || 'default'}>{statusLabel[status] || status}</Tag>;
}
