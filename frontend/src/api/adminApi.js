import { apiClient } from "./client";

export const adminApi = {
  listUsers: () => apiClient.get("/users").then((response) => response.data),
  listPositionTemplates: () =>
    apiClient
      .get("/users/position-templates")
      .then((response) => response.data),
  createUser: (data) =>
    apiClient.post("/users", data).then((response) => response.data),
  updateUser: (userId, data) =>
    apiClient.patch(`/users/${userId}`, data).then((response) => response.data),
  resetPassword: (userId, newPassword) =>
    apiClient
      .patch(`/users/${userId}/reset-password`, { new_password: newPassword })
      .then((response) => response.data),
  deactivateUser: (userId) =>
    apiClient.delete(`/users/${userId}`).then((response) => response.data),
  activateUser: (userId) =>
    apiClient
      .patch(`/users/${userId}`, { is_active: true })
      .then((response) => response.data),
  deleteUserHard: (userId) =>
    apiClient.delete(`/users/${userId}/hard`).then((response) => response.data),
  listDepartments: () =>
    apiClient.get("/departments").then((response) => response.data),
};
