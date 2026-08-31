import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 120000,
});

// Attach the current access token to every API request.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("kpi_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Clear invalid sessions and return to login after an unauthorized response.
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("kpi_access_token");
      localStorage.removeItem("kpi_user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  },
);
