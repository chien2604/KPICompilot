import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api',
  timeout: 120000, // Tăng timeout của client lên 120 giây (2 phút) để đồng bộ với LLM
});
