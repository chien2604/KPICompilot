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

export const roleLabel = {
  LEADER: 'Lãnh đạo Sở',
  MANAGER: 'Lãnh đạo phòng',
  STAFF: 'Chuyên viên',
};

export const kpiTemplateLabel = {
  BAN_GIAM_DOC: 'Ban Giám đốc',
  TRUONG_PHO_PHONG: 'Trưởng/Phó phòng',
  CONG_CHUC_KHONG_CHUC_VU: 'Công chức không chức vụ',
};

export const riskLevelLabel = {
  LOW: 'Thấp',
  MEDIUM: 'Trung bình',
  HIGH: 'Cao',
};

export const riskColor = (score) => {
  if (score >= 85) return '#22c55e'; // Green (High)
  if (score >= 70) return '#f59e0b'; // Amber (Medium)
  return '#ef4444'; // Red (Low)
};

export const formatDate = (value) => (value ? new Date(value).toLocaleDateString('vi-VN') : '-');
