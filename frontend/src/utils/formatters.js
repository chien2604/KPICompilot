export const statusLabel = {
  COMPLETED: "Hoàn thành",
  IN_PROGRESS: "Đang thực hiện",
  OVERDUE: "Quá hạn",
  NOT_STARTED: "Chưa bắt đầu",
  UPLOADED: "Đã upload",
  PROCESSING: "Đang xử lý",
  ANALYZED: "Đã phân tích",
  FAILED: "Lỗi",
};

export const roleLabel = {
  admin: "Quản trị viên",
  user: "Người dùng",
};

export const kpiTemplateLabel = {
  ADMIN: "Quản trị hệ thống",
  LANH_DAO_XA: "Lãnh đạo HĐND, UBND xã",
  LANH_DAO_DON_VI: "Trưởng đơn vị",
  PHO_LANH_DAO_DON_VI: "Phó trưởng đơn vị",
  CHUYEN_MON_NGHIEP_VU: "Công chức chuyên môn, nghiệp vụ",
  CHUA_THUOC_PHAM_VI_KPI: "Viên chức chưa thuộc phạm vi KPI",
};

export const organizationRoleLabel = {
  LEADERSHIP: "Lãnh đạo HĐND, UBND xã",
  UNIT_HEAD: "Trưởng đơn vị",
  UNIT_DEPUTY: "Phó trưởng đơn vị",
  SPECIALIST: "Công chức chuyên môn, nghiệp vụ",
  OUT_OF_SCOPE: "Chưa thuộc phạm vi KPI",
};

export const riskLevelLabel = {
  LOW: "Thấp",
  MEDIUM: "Trung bình",
  HIGH: "Cao",
};

/** Map a KPI score to the configured risk color. */
export const riskColor = (score) => {
  if (score >= 85) return "#22c55e";
  if (score >= 70) return "#f59e0b";
  return "#ef4444";
};

/** Format an optional date for Vietnamese display. */
export const formatDate = (value) =>
  value ? new Date(value).toLocaleDateString("vi-VN") : "-";
