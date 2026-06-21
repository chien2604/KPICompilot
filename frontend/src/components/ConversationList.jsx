import { Empty } from 'antd';
import ConversationItem from './ConversationItem';

export default function ConversationList({ conversations, activeId, onSelect, onDelete }) {
  if (!conversations.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Chưa có hội thoại" />;
  }

  return (
    <div className="conversation-list">
      {conversations.map((conversation) => (
        <ConversationItem
          key={conversation.conversation_id}
          conversation={conversation}
          active={conversation.conversation_id === activeId}
          onSelect={onSelect}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
