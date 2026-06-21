import { apiClient } from './client';

export const conversationApi = {
  create: (payload) => apiClient.post('/conversations', payload).then((res) => res.data),
  list: (params) => apiClient.get('/conversations', { params }).then((res) => res.data),
  get: (id, params) => apiClient.get(`/conversations/${id}`, { params }).then((res) => res.data),
  remove: (id, params) => apiClient.delete(`/conversations/${id}`, { params }).then((res) => res.data),
};
