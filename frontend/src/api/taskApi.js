import { apiClient } from './client';

export const taskApi = {
  list: (params) => apiClient.get('/tasks', { params }).then((res) => res.data),
  stats: () => apiClient.get('/tasks/stats').then((res) => res.data),
  create: (payload) => apiClient.post('/tasks', payload).then((res) => res.data),
  update: (id, payload) => apiClient.patch(`/tasks/${id}`, payload).then((res) => res.data),
  updateStatus: (id, payload) => apiClient.patch(`/tasks/${id}/status`, payload).then((res) => res.data),
  remove: (id) => apiClient.delete(`/tasks/${id}`).then((res) => res.data),
};
