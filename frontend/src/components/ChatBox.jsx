import { Button, Input, List } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { useState } from 'react';

export default function ChatBox({ onSend, loading }) {
  const [value, setValue] = useState('');
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Lãnh đạo có thể hỏi về KPI rủi ro, phòng chậm tiến độ, lý do điểm thấp hoặc sinh báo cáo giao ban.' },
  ]);

  const submit = async () => {
    if (!value.trim()) return;
    const question = value.trim();
    setMessages((items) => [...items, { role: 'user', text: question }]);
    setValue('');
    const answer = await onSend(question);
    setMessages((items) => [...items, { role: 'assistant', text: answer }]);
  };

  return (
    <div className="chatbox">
      <List
        dataSource={messages}
        renderItem={(item) => <List.Item className={`chatbox__msg chatbox__msg--${item.role}`}>{item.text}</List.Item>}
      />
      <Input.Search
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onSearch={submit}
        enterButton={<Button type="primary" icon={<SendOutlined />} loading={loading} />}
        placeholder="Nhập câu hỏi tiếng Việt..."
      />
    </div>
  );
}
