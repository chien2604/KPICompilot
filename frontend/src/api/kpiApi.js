import { apiClient } from "./client";

export const kpiApi = {
  dashboard: (month) =>
    apiClient
      .get("/kpi/dashboard", { params: month ? { month } : {} })
      .then((response) => response.data),
  heatmap: (month) =>
    apiClient
      .get("/kpi/heatmap", { params: month ? { month } : {} })
      .then((response) => response.data),
  profile: (userId, month) =>
    apiClient
      .get(`/kpi/users/${userId}/profile`, { params: month ? { month } : {} })
      .then((response) => response.data),
  score: (userId, month) =>
    apiClient
      .get(`/kpi/users/${userId}/score`, { params: month ? { month } : {} })
      .then((response) => response.data),
  recompute: (userId, month) =>
    apiClient
      .post(`/kpi/users/${userId}/score/recompute`, null, {
        params: month ? { month } : {},
      })
      .then((response) => response.data),
  criteria: (role_template) =>
    apiClient
      .get("/kpi/criteria", { params: { role_template } })
      .then((res) => res.data),
  ranking: (params) =>
    apiClient.get("/kpi/ranking", { params }).then((res) => res.data),
  workCatalog: (userId) =>
    apiClient
      .get("/kpi/work-catalog", { params: userId ? { user_id: userId } : {} })
      .then((res) => res.data),
  assessmentInputs: (userId, month) =>
    apiClient
      .get(`/kpi/users/${userId}/assessment-inputs`, {
        params: month ? { month } : {},
      })
      .then((res) => res.data),
  saveAssessmentInputs: (userId, payload, month) =>
    apiClient
      .put(`/kpi/users/${userId}/assessment-inputs`, payload, {
        params: month ? { month } : {},
      })
      .then((res) => res.data),
  saveSelfAssessment: (userId, payload, month) =>
    apiClient
      .put(`/kpi/users/${userId}/self-assessment`, payload, {
        params: month ? { month } : {},
      })
      .then((res) => res.data),
  reviewAssessment: (userId, payload, month) =>
    apiClient
      .put(`/kpi/users/${userId}/review`, payload, {
        params: month ? { month } : {},
      })
      .then((res) => res.data),
  confirmScore: (userId, month) =>
    apiClient
      .post(`/kpi/users/${userId}/score/confirm`, null, {
        params: month ? { month } : {},
      })
      .then((res) => res.data),
};
