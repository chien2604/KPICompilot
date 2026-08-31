import {
  Button,
  Card,
  Progress,
  Space,
  Tooltip,
  Typography,
  message,
} from "antd";
import {
  BookOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  TrophyOutlined,
} from "@ant-design/icons";
import { useEffect, useState } from "react";
import { chatbotApi } from "../api/chatbotApi";
import { conversationApi } from "../api/conversationApi";
import { kpiApi } from "../api/kpiApi";
import ChatBox from "../components/ChatBox";
import ConversationSidebar from "../components/ConversationSidebar";
import { useAuth } from "../contexts/AuthContext";

/** Render account-scoped conversations and Copilot messages. */
export default function CopilotChatPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [sidebarLoading, setSidebarLoading] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [dashboard, setDashboard] = useState(null);

  /** Load conversations owned by the current account. */
  const loadConversations = async () => {
    const rows = await conversationApi.list();
    setConversations(rows);
    return rows;
  };

  /** Load one owned conversation and its messages. */
  const loadConversation = async (conversationId) => {
    const detail = await conversationApi.get(conversationId);
    setActiveId(detail.conversation.conversation_id);
    setMessages(detail.messages || []);
    return detail;
  };

  /** Create a new conversation for the authenticated account. */
  const createConversation = async () => {
    setSidebarLoading(true);
    try {
      const conversation = await conversationApi.create({});
      setConversations((items) => [conversation, ...items]);
      setActiveId(conversation.conversation_id);
      setMessages([]);
      return conversation;
    } finally {
      setSidebarLoading(false);
    }
  };

  /** Restore the most recent conversation after login or page reload. */
  const bootstrap = async () => {
    try {
      const rows = await loadConversations();
      if (rows[0]) {
        await loadConversation(rows[0].conversation_id);
      } else {
        // Don't create a default conversation — start with empty state
        setActiveId(null);
        setMessages([]);
      }
    } catch (error) {
      message.error("Không tải được lịch sử hội thoại");
    }
  };

  useEffect(() => {
    bootstrap();
    kpiApi
      .dashboard()
      .then(setDashboard)
      .catch(() => setDashboard(null));
  }, [user?.user_id]);

  const taskCompletion = dashboard?.task_total
    ? Math.round((dashboard.task_completed / dashboard.task_total) * 100)
    : 0;
  const suggestions = [
    "Phân tích kết quả KPI của đơn vị",
    "Đơn vị nào đang có rủi ro?",
    "Vì sao có nhiệm vụ quá hạn?",
    "Gợi ý nội dung giao ban tuần",
  ];

  /** Send one message and reload persisted conversation state. */
  const send = async (question) => {
    setLoading(true);
    const optimisticUserMessage = {
      message_id: `local-${Date.now()}`,
      conversation_id: activeId,
      role: "user",
      content: question,
      created_at: new Date().toISOString(),
    };
    setMessages((items) => [...items, optimisticUserMessage]);
    try {
      let conversationId = activeId;
      if (!conversationId) {
        // Lazy creation: only create conversation on first message
        const conversation = await createConversation();
        conversationId = conversation.conversation_id;
      }
      const response = await chatbotApi.send({
        conversation_id: conversationId,
        message: question,
      });
      await loadConversation(response.conversation_id || conversationId);
      await loadConversations();
    } catch (error) {
      message.error("Không gọi được AI Copilot");
      setMessages((items) => [
        ...items,
        {
          message_id: `error-${Date.now()}`,
          conversation_id: activeId,
          role: "assistant",
          content: "Chưa gọi được chatbot backend.",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  /** Soft-delete one conversation and select the next available item. */
  const removeConversation = async (conversationId) => {
    try {
      await conversationApi.remove(conversationId);
      const rows = await loadConversations();
      if (activeId === conversationId) {
        if (rows[0]) {
          await loadConversation(rows[0].conversation_id);
        } else {
          // No conversations left — reset to empty state
          setActiveId(null);
          setMessages([]);
        }
      }
    } catch (error) {
      message.error("Không xóa được hội thoại");
    }
  };

  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-intro">
        <div>
          <Typography.Title level={3}>AI Copilot Chat</Typography.Title>
          <Typography.Text>
            Trợ lý phân tích KPI, tiến độ nhiệm vụ và dữ liệu điều hành
          </Typography.Text>
        </div>
        <Tooltip
          title={
            sidebarOpen ? "Ẩn danh sách hội thoại" : "Hiện danh sách hội thoại"
          }
        >
          <Button
            icon={sidebarOpen ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />}
            onClick={() => setSidebarOpen((v) => !v)}
          />
        </Tooltip>
      </div>
      <div
        className={`copilot-layout ${sidebarOpen ? "" : "copilot-layout--collapsed"}`}
      >
        {sidebarOpen && (
          <ConversationSidebar
            conversations={conversations}
            activeId={activeId}
            loading={sidebarLoading}
            onCreate={() => createConversation()}
            onSelect={(conversationId) =>
              loadConversation(conversationId).catch(() =>
                message.error("Không tải được hội thoại"),
              )
            }
            onDelete={removeConversation}
          />
        )}
        <Card className="copilot-chat-card">
          <ChatBox
            messages={messages}
            onSend={send}
            loading={loading}
            suggestions={suggestions}
          />
        </Card>
        <aside className="copilot-context-panel">
          <div className="copilot-context-panel__title">Thông tin nhanh</div>
          <div className="copilot-context-metric">
            <span className="copilot-context-metric__icon copilot-context-metric__icon--green">
              <TrophyOutlined />
            </span>
            <small>Điểm KPI hiện tại</small>
            <strong>
              {dashboard?.avg_kpi ?? "—"}
              <em>/100</em>
            </strong>
          </div>
          <div className="copilot-context-metric">
            <span className="copilot-context-metric__icon copilot-context-metric__icon--blue">
              <CheckCircleOutlined />
            </span>
            <small>Tiến độ nhiệm vụ</small>
            <strong>
              {taskCompletion}
              <em>%</em>
            </strong>
            <Progress percent={taskCompletion} showInfo={false} size="small" />
          </div>
          <div className="copilot-context-metric">
            <span className="copilot-context-metric__icon copilot-context-metric__icon--orange">
              <ClockCircleOutlined />
            </span>
            <small>Nhiệm vụ quá hạn</small>
            <strong>
              {dashboard?.task_overdue ?? "—"}
              <em> nhiệm vụ</em>
            </strong>
          </div>
          <div className="copilot-reference-list">
            <div className="copilot-context-panel__title">
              Tài liệu tham chiếu
            </div>
            <span>
              <BookOutlined /> Nghị định 335/2025/NĐ-CP
            </span>
            <span>
              <BookOutlined /> Quy định đánh giá KPI
            </span>
            <span>
              <BookOutlined /> Dữ liệu nhiệm vụ và minh chứng
            </span>
          </div>
        </aside>
      </div>
    </Space>
  );
}
