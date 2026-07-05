import { apiClient } from './client';

export const taskApi = {
  list: (params) => apiClient.get('/tasks', { params }).then((res) => res.data),
  stats: () => apiClient.get('/tasks/stats').then((res) => res.data),
  create: (payload) => apiClient.post('/tasks', payload).then((res) => res.data),
  update: (id, payload) => apiClient.patch(`/tasks/${id}`, payload).then((res) => res.data),
  updateStatus: (id, payload) => apiClient.patch(`/tasks/${id}/status`, payload).then((res) => res.data),
  remove: (id) => apiClient.delete(`/tasks/${id}`).then((res) => res.data),
  scoreAssignment: (taskId, userId, leaderScore) =>
    apiClient.patch(`/tasks/${taskId}/assignments/${userId}/score`, null, {
      params: { leader_score: leaderScore },
    }).then((res) => res.data),
};
