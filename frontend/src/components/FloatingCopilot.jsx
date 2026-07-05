import { useState, useEffect, useRef } from 'react';
import { Button, Input } from 'antd';
import { CloseOutlined, RobotOutlined, SendOutlined, UserOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { chatbotApi } from '../api/chatbotApi';
import { conversationApi } from '../api/conversationApi';
import { useAuth } from '../contexts/AuthContext';

// Lấy tháng hiện tại dạng YYYY-MM
const getCurrentMonth = () => new Date().toISOString().slice(0, 7);

export default function FloatingCopilot() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [value, setValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [convId, setConvId] = useState(null);
  const bottomRef = useRef(null);

  // Drag state
  const [pos, setPos] = useState({ right: 28, bottom: 28 });
  const dragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0, right: 0, bottom: 0 });
  const containerRef = useRef(null);

  const onMouseDown = (e) => {
    // Chỉ drag khi click vào nút, không phải popup
    if (e.target.closest('.floating-copilot__popup')) return;
    dragging.current = true;
    dragStart.current = {
      x: e.clientX,
      y: e.clientY,
      right: pos.right,
      bottom: pos.bottom,
    };
    e.preventDefault();
  };

  useEffect(() => {
    const onMouseMove = (e) => {
      if (!dragging.current) return;
      const dx = dragStart.current.x - e.clientX;
      const dy = dragStart.current.y - e.clientY;
      const newRight = Math.max(8, Math.min(window.innerWidth - 68, dragStart.current.right + dx));
      const newBottom = Math.max(8, Math.min(window.innerHeight - 68, dragStart.current.bottom + dy));
      setPos({ right: newRight, bottom: newBottom });
    };
    const onMouseUp = () => { dragging.current = false; };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, [pos]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    if (!value.trim() || loading) return;
    const question = value.trim();
    setValue('');

    setMessages((prev) => [...prev, { role: 'user', content: question, id: Date.now() }]);
    setLoading(true);

    try {
      let cid = convId;
      if (!cid) {
        // Tạo conversation mới — user_id lấy từ token phía backend
        const conv = await conversationApi.create({ user_id: user?.user_id });
        cid = conv.conversation_id;
        setConvId(cid);
      }
      // Gửi message — user_id KHÔNG cần trong body, backend đọc từ JWT Authorization header
      const res = await chatbotApi.send({
        conversation_id: cid,
        message: question,
        month: getCurrentMonth(),
        department_id: user?.department_id ?? null,
      });
      const detail = await conversationApi.get(res.conversation_id || cid, { user_id: user?.user_id });
      const msgs = detail.messages || [];
      setMessages(msgs.map((m, i) => ({ role: m.role, content: m.content, id: i })));
    } catch {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: 'Không kết nối được AI. Vui lòng thử lại.',
        id: Date.now(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const toggleOpen = () => {
    setOpen((v) => !v);
  };

  return (
    <div
      className="floating-copilot"
      ref={containerRef}
      style={{ right: pos.right, bottom: pos.bottom }}
      onMouseDown={onMouseDown}
    >
      {/* Popup chat */}
      {open && (
        <div className="floating-copilot__popup">
          <div className="floating-copilot__header">
            <div className="floating-copilot__header-left">
              <RobotOutlined style={{ fontSize: 20 }} />
              <span>AI KPI Copilot</span>
            </div>
            <button className="floating-copilot__close" onClick={() => setOpen(false)}>
              <CloseOutlined />
            </button>
          </div>

          <div className="floating-copilot__messages">
            {messages.length === 0 && (
              <div className="floating-copilot__empty">
                <RobotOutlined style={{ fontSize: 36, color: '#cbd5e1' }} />
                <p>Xin chào! Tôi có thể giúp gì cho bạn?</p>
              </div>
            )}
            {messages.map((msg) => (
              <div key={msg.id} className={`floating-copilot__msg floating-copilot__msg--${msg.role}`}>
                <div className={`floating-copilot__avatar floating-copilot__avatar--${msg.role}`}>
                  {msg.role === 'assistant' ? <RobotOutlined /> : <UserOutlined />}
                </div>
                <div className={`floating-copilot__bubble floating-copilot__bubble--${msg.role}`}>
                  <div className="ai-markdown-container" style={{ fontSize: 14 }}>
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="floating-copilot__msg floating-copilot__msg--assistant">
                <div className="floating-copilot__avatar floating-copilot__avatar--assistant"><RobotOutlined /></div>
                <div className="floating-copilot__bubble floating-copilot__bubble--assistant floating-copilot__bubble--typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="floating-copilot__input-wrap">
            <Input.TextArea
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Nhập câu hỏi..."
              autoSize={{ minRows: 1, maxRows: 3 }}
              disabled={loading}
              style={{ fontSize: 14, borderRadius: 10 }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={send}
              loading={loading}
              disabled={!value.trim()}
              style={{ borderRadius: 10, height: 36, width: 36 }}
            />
          </div>
        </div>
      )}

      {/* Nút nổi */}
      <button
        className={`floating-copilot__btn ${open ? 'floating-copilot__btn--active' : ''}`}
        onClick={toggleOpen}
        aria-label="AI Copilot"
      >
        {open ? <CloseOutlined style={{ fontSize: 22 }} /> : <RobotOutlined style={{ fontSize: 26 }} />}
      </button>
    </div>
  );
}
