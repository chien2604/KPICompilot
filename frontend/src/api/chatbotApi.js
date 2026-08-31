import { apiClient } from "./client";

export const chatbotApi = {
  send: (payload) =>
    apiClient.post("/chatbot/message", payload).then((res) => res.data),
};
