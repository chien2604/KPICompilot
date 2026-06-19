export const statusLabel = {
  COMPLETED: 'Hoàn thành',
  IN_PROGRESS: 'Đang thực hiện',
  OVERDUE: 'Quá hạn',
  NOT_STARTED: 'Chưa bắt đầu',
  UPLOADED: 'Đã upload',
  PROCESSING: 'Đang xử lý',
  ANALYZED: 'Đã phân tích',
  FAILED: 'Lỗi',
};

export const riskColor = (score) => {
  if (score >= 85) return '#16a34a';
  if (score >= 70) return '#f59e0b';
  return '#dc2626';
};

export const formatDate = (value) => (value ? new Date(value).toLocaleDateString('vi-VN') : '-');
