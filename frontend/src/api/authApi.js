import { apiClient } from "./client";

export const authApi = {
  login: (email, password) =>
    apiClient.post("/auth/login", { email, password }).then((r) => r.data),

  me: () => apiClient.get("/auth/me").then((r) => r.data),

  assignableUsers: () =>
    apiClient.get("/auth/assignable-users").then((r) => r.data),

  changePassword: (oldPassword, newPassword) =>
    apiClient
      .post("/auth/change-password", {
        old_password: oldPassword,
        new_password: newPassword,
      })
      .then((r) => r.data),

  changePasswordPublic: (email, oldPassword, newPassword) =>
    apiClient
      .post("/auth/change-password-public", {
        email,
        old_password: oldPassword,
        new_password: newPassword,
      })
      .then((r) => r.data),
};
