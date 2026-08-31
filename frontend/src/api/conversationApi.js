import { apiClient } from "./client";

export const conversationApi = {
  create: (payload = {}) =>
    apiClient.post("/conversations", payload).then((response) => response.data),
  list: () => apiClient.get("/conversations").then((response) => response.data),
  get: (id) =>
    apiClient.get(`/conversations/${id}`).then((response) => response.data),
  remove: (id) =>
    apiClient.delete(`/conversations/${id}`).then((response) => response.data),
};
