import { apiClient } from './client';

export const reportApi = {
  list: () => apiClient.get('/reports').then((res) => res.data),

  // QUAN TRỌNG: sinh báo cáo gọi LLM, có thể retry 1 lần nếu LLM trả sai format
  // (xem ai_layer/report_generator.py ở backend) — tổng thời gian có thể vượt
  // quá timeout mặc định 30s của apiClient, khiến axios tự huỷ request dù
  // backend vẫn chạy tiếp và lưu DB thành công (đây là lý do "F5 mới thấy").
  // Dùng timeout riêng dài hơn (120s) CHỈ cho request này.
  generate: (payload) => apiClient.post('/reports/generate', payload, { timeout: 120000 }).then((res) => res.data),

  update: (id, content) => apiClient.patch(`/reports/${id}`, { content }).then((res) => res.data),
  remove: (id) => apiClient.delete(`/reports/${id}`).then((res) => res.data),
  get: (id) => apiClient.get(`/reports/${id}`).then((res) => res.data),

  // Render PDF qua Puppeteer cũng có thể chậm hơn timeout mặc định, đặc biệt
  // lần đầu khởi động Chromium — tăng timeout riêng cho export PDF.
  exportPdf: (id) =>
    apiClient.get(`/reports/${id}/export/pdf`, { responseType: 'blob', timeout: 60000 }).then((res) => res.data),
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