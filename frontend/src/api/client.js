import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 120000,
});

// Tự động gắn Authorization header từ localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('kpi_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 → xoá token + chuyển về login
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('kpi_access_token');
      localStorage.removeItem('kpi_user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  },
);
