import { Button, Tooltip } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';

export default function ConversationItem({ conversation, active, onSelect, onDelete }) {
  return (
    <div className={`conversation-item ${active ? 'conversation-item--active' : ''}`} onClick={() => onSelect(conversation.conversation_id)}>
      <span className="conversation-item__title">{conversation.title || 'Cuộc hội thoại mới'}</span>
      <Tooltip title="Xóa hội thoại">
        <Button
          type="text"
          size="small"
          icon={<DeleteOutlined />}
          onClick={(event) => {
            event.stopPropagation();
            onDelete(conversation.conversation_id);
          }}
        />
      </Tooltip>
    </div>
  );
}
