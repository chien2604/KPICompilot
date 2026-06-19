import { apiClient } from './client';

export const reportApi = {
  list: () => apiClient.get('/reports').then((res) => res.data),
  generate: (payload) => apiClient.post('/reports/generate', payload).then((res) => res.data),
  get: (id) => apiClient.get(`/reports/${id}`).then((res) => res.data),
};
