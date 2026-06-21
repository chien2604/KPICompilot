import { Button } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import ConversationList from './ConversationList';

export default function ConversationSidebar({ conversations, activeId, loading, onCreate, onSelect, onDelete }) {
  return (
    <aside className="conversation-sidebar">
      <Button type="primary" icon={<PlusOutlined />} block onClick={onCreate} loading={loading}>
        Cuộc hội thoại mới
      </Button>
      <ConversationList conversations={conversations} activeId={activeId} onSelect={onSelect} onDelete={onDelete} />
    </aside>
  );
}
