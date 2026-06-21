import { Button, Empty, Input, List } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { useState } from 'react';

export default function ChatBox({ messages = [], onSend, loading }) {
  const [value, setValue] = useState('');

  const submit = async () => {
    if (!value.trim()) return;
    const question = value.trim();
    setValue('');
    await onSend(question);
  };

  return (
    <div className="chatbox">
      <List
        dataSource={messages}
        locale={{ emptyText: <Empty description="Bắt đầu cuộc hội thoại mới" /> }}
        renderItem={(item) => <List.Item className={`chatbox__msg chatbox__msg--${item.role}`}>{item.content}</List.Item>}
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
