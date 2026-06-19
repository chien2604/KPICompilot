import { apiClient } from './client';

export const userApi = {
  list: () => apiClient.get('/users').then((res) => res.data),
  get: (id) => apiClient.get(`/users/${id}`).then((res) => res.data),
  departments: () => apiClient.get('/departments').then((res) => res.data),
  departmentUsers: (id) => apiClient.get(`/departments/${id}/users`).then((res) => res.data),
};
