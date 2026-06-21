import { apiClient } from './client';

export const reportApi = {
  list: () => apiClient.get('/reports').then((res) => res.data),
  generate: (payload) => apiClient.post('/reports/generate', payload).then((res) => res.data),
  get: (id) => apiClient.get(`/reports/${id}`).then((res) => res.data),
  update: (id, content) => apiClient.patch(`/reports/${id}`, { content }).then((res) => res.data),
  remove: (id) => apiClient.delete(`/reports/${id}`).then((res) => res.data),

  // Trả về Blob để trigger download trực tiếp trên browser
  exportPdf: (id) =>
    apiClient.get(`/reports/${id}/export/pdf`, { responseType: 'blob' }).then((res) => res.data),
  exportDocx: (id) =>
    apiClient.get(`/reports/${id}/export/docx`, { responseType: 'blob' }).then((res) => res.data),
};

/** Helper: trigger download của 1 Blob trên browser với tên file cho trước. */
export function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}