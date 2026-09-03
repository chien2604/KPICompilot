import { apiClient } from "./client";

export const evidenceApi = {
  list: (params) =>
    apiClient
      .get("/evidences", { params: { ...params, _t: Date.now() } })
      .then((res) => res.data),
  get: (id) =>
    apiClient
      .get(`/evidences/${id}`, { params: { _t: Date.now() } })
      .then((res) => res.data),
  analysis: (id) =>
    apiClient
      .get(`/evidences/${id}/analysis`, { params: { _t: Date.now() } })
      .then((res) => res.data),
  analyze: (id) =>
    apiClient.post(`/evidences/${id}/analyze`).then((res) => res.data),
  upload: ({ task_id, assignment_id, file }) => {
    const form = new FormData();
    form.append("task_id", task_id);
    form.append("assignment_id", assignment_id);
    form.append("file", file);
    return apiClient
      .post("/evidences/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((res) => res.data);
  },
  createReference: (payload) =>
    apiClient.post("/evidences/reference", payload).then((res) => res.data),
  verify: (id, payload) =>
    apiClient.patch(`/evidences/${id}/verify`, payload).then((res) => res.data),
};
