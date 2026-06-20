import { apiClient } from './client';

export const evidenceApi = {
  list: (params) => apiClient.get('/evidences', { params }).then((res) => res.data),
  get: (id) => apiClient.get(`/evidences/${id}`).then((res) => res.data),
  analysis: (id) => apiClient.get(`/evidences/${id}/analysis`).then((res) => res.data),
  analyze: (id) => apiClient.post(`/evidences/${id}/analyze`).then((res) => res.data),
  upload: ({ task_id, uploaded_by, file }) => {
    const form = new FormData();
    form.append('task_id', task_id);
    form.append('uploaded_by', uploaded_by);
    form.append('file', file);
    return apiClient.post('/evidences/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then((res) => res.data);
  },
};
