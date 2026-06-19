import { Card, Col, Row, Space, Typography, message } from 'antd';
import { useState } from 'react';
import { chatbotApi } from '../api/chatbotApi';
import ChatBox from '../components/ChatBox';

export default function CopilotChatPage() {
  const [loading, setLoading] = useState(false);
  const [lastData, setLastData] = useState(null);
  const send = async (question) => {
    setLoading(true);
    try {
      const response = await chatbotApi.send({
        user_id: Number(localStorage.getItem('selected_user_id') || 1),
        message: question,
        month: '2026-06',
      });
      setLastData(response);
      return response.answer;
    } catch (error) {
      message.error('Không gọi được chatbot');
      return 'Chưa gọi được chatbot backend.';
    } finally {
      setLoading(false);
    }
  };

  return (
    <Space direction="vertical" size={18} className="page">
      <Typography.Title level={3}>AI Copilot Chat</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}><Card><ChatBox onSend={send} loading={loading} /></Card></Col>
        <Col xs={24} lg={8}>
          <Card title="Dữ liệu trả về">
            <pre className="text-preview">{JSON.stringify(lastData?.data || {}, null, 2)}</pre>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
