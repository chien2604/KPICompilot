import { Card, Space, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { chatbotApi } from '../api/chatbotApi';
import { conversationApi } from '../api/conversationApi';
import ChatBox from '../components/ChatBox';
import ConversationSidebar from '../components/ConversationSidebar';

const getSelectedUserId = () => Number(localStorage.getItem('selected_user_id') || 1);

export default function CopilotChatPage() {
  const [loading, setLoading] = useState(false);
  const [sidebarLoading, setSidebarLoading] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);

  const loadConversations = async (userId = getSelectedUserId()) => {
    const rows = await conversationApi.list({ user_id: userId });
    setConversations(rows);
    return rows;
  };

  const loadConversation = async (conversationId, userId = getSelectedUserId()) => {
    const detail = await conversationApi.get(conversationId, { user_id: userId });
    setActiveId(detail.conversation.conversation_id);
    setMessages(detail.messages || []);
    return detail;
  };

  const createConversation = async (userId = getSelectedUserId()) => {
    setSidebarLoading(true);
    try {
      const conversation = await conversationApi.create({ user_id: userId });
      setConversations((items) => [conversation, ...items]);
      setActiveId(conversation.conversation_id);
      setMessages([]);
      return conversation;
    } finally {
      setSidebarLoading(false);
    }
  };

  const bootstrap = async (userId = getSelectedUserId()) => {
    try {
      const rows = await loadConversations(userId);
      if (rows[0]) {
        await loadConversation(rows[0].conversation_id, userId);
      } else {
        await createConversation(userId);
      }
    } catch (error) {
      message.error('Không tải được lịch sử hội thoại');
    }
  };

  useEffect(() => {
    bootstrap();
    const handleUserChange = (event) => {
      const nextUserId = Number(event.detail || getSelectedUserId());
      setActiveId(null);
      setMessages([]);
      bootstrap(nextUserId);
    };
    window.addEventListener('demo-user-change', handleUserChange);
    return () => window.removeEventListener('demo-user-change', handleUserChange);
  }, []);

  const send = async (question) => {
    setLoading(true);
    const userId = getSelectedUserId();
    const optimisticUserMessage = {
      message_id: `local-${Date.now()}`,
      conversation_id: activeId,
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    };
    setMessages((items) => [...items, optimisticUserMessage]);
    try {
      let conversationId = activeId;
      if (!conversationId) {
        const conversation = await createConversation(userId);
        conversationId = conversation.conversation_id;
      }
      const response = await chatbotApi.send({
        user_id: userId,
        conversation_id: conversationId,
        message: question,
        month: '2026-06',
      });
      await loadConversation(response.conversation_id || conversationId, userId);
      await loadConversations(userId);
    } catch (error) {
      message.error('Không gọi được AI Copilot');
      setMessages((items) => [
        ...items,
        {
          message_id: `error-${Date.now()}`,
          conversation_id: activeId,
          role: 'assistant',
          content: 'Chưa gọi được chatbot backend.',
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const removeConversation = async (conversationId) => {
    const userId = getSelectedUserId();
    try {
      await conversationApi.remove(conversationId, { user_id: userId });
      const rows = await loadConversations(userId);
      if (activeId === conversationId) {
        if (rows[0]) {
          await loadConversation(rows[0].conversation_id, userId);
        } else {
          await createConversation(userId);
        }
      }
    } catch (error) {
      message.error('Không xóa được hội thoại');
    }
  };

  return (
    <Space direction="vertical" size={18} className="page">
      <Typography.Title level={3}>AI Copilot Chat</Typography.Title>
      <div className="copilot-layout">
        <ConversationSidebar
          conversations={conversations}
          activeId={activeId}
          loading={sidebarLoading}
          onCreate={() => createConversation()}
          onSelect={(conversationId) => loadConversation(conversationId).catch(() => message.error('Không tải được hội thoại'))}
          onDelete={removeConversation}
        />
        <Card className="copilot-chat-card">
          <ChatBox messages={messages} onSend={send} loading={loading} />
        </Card>
      </div>
    </Space>
  );
}
