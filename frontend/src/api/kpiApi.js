import { apiClient } from './client';

export const kpiApi = {
  dashboard: (month = '2026-06') => apiClient.get('/kpi/dashboard', { params: { month } }).then((res) => res.data),
  heatmap: (month = '2026-06') => apiClient.get('/kpi/heatmap', { params: { month } }).then((res) => res.data),
  profile: (userId, month = '2026-06') => apiClient.get(`/kpi/users/${userId}/profile`, { params: { month } }).then((res) => res.data),
  score: (userId, month = '2026-06') => apiClient.get(`/kpi/users/${userId}/score`, { params: { month } }).then((res) => res.data),
  recompute: (userId, month = '2026-06') => apiClient.post(`/kpi/users/${userId}/score/recompute`, null, { params: { month } }).then((res) => res.data),
  criteria: (role_template) => apiClient.get('/kpi/criteria', { params: { role_template } }).then((res) => res.data),
  ranking: (params) => apiClient.get('/kpi/ranking', { params }).then((res) => res.data),
};
