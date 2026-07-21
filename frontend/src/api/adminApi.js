import { apiClient } from './client';

export const adminApi = {
  // Lấy tất cả users (admin thấy toàn bộ)
  listUsers: () => apiClient.get('/users').then((r) => r.data),

  // Tạo tài khoản người dùng mới
  createUser: (data) => apiClient.post('/users', data).then((r) => r.data),

  // Cập nhật phân quyền user (role, position, department, is_active)
  updateUserRole: (userId, data) =>
    apiClient.patch(`/users/${userId}/role`, data).then((r) => r.data),

  // Đặt lại mật khẩu cho user
  resetPassword: (userId, newPassword) =>
    apiClient
      .patch(`/users/${userId}/reset-password`, { new_password: newPassword })
      .then((r) => r.data),

  // Vô hiệu hoá tài khoản (soft delete)
  deactivateUser: (userId) => apiClient.delete(`/users/${userId}`).then((r) => r.data),

  // Kích hoạt lại tài khoản
  activateUser: (userId) =>
    apiClient.patch(`/users/${userId}/role`, { is_active: true }).then((r) => r.data),

  // Lấy danh sách phòng ban
  listDepartments: () => apiClient.get('/departments').then((r) => r.data),
};
