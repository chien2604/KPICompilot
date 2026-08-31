import { Button, Empty, Input } from "antd";
import { RobotOutlined, SendOutlined, UserOutlined } from "@ant-design/icons";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

/** Render the chat box interface. */
export default function ChatBox({
  messages = [],
  onSend,
  loading,
  suggestions = [],
}) {
  const [value, setValue] = useState("");
  const bottomRef = useRef(null);

  // Auto-scroll xuống cuối khi có tin mới
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /** Handle the submit operation. */
  const submit = async () => {
    if (!value.trim() || loading) return;
    const question = value.trim();
    setValue("");
    await onSend(question);
  };

  /** Handle the key down. */
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="chatbox2">
      {/* Vùng tin nhắn */}
      <div className="chatbox2__messages">
        {messages.length === 0 ? (
          <div className="chatbox2__empty">
            <RobotOutlined className="chatbox2__empty-icon" />
            <div className="chatbox2__empty-title">AI KPI Copilot</div>
            <div className="chatbox2__empty-sub">
              Hỏi tôi về KPI, nhiệm vụ, hoặc hiệu suất cán bộ
            </div>
            <div className="chatbox2__suggestions">
              {suggestions.map((suggestion) => (
                <button
                  type="button"
                  key={suggestion}
                  onClick={() => onSend(suggestion)}
                  disabled={loading}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.message_id}
              className={`chatbox2__msg chatbox2__msg--${msg.role}`}
            >
              <div className={`chatbox2__avatar chatbox2__avatar--${msg.role}`}>
                {msg.role === "assistant" ? (
                  <RobotOutlined />
                ) : (
                  <UserOutlined />
                )}
              </div>
              <div className={`chatbox2__bubble chatbox2__bubble--${msg.role}`}>
                <div className="ai-markdown-container">
                  <ReactMarkdown>{msg.content || ""}</ReactMarkdown>
                </div>
              </div>
            </div>
          ))
        )}

        {/* Loading bubble */}
        {loading && (
          <div className="chatbox2__msg chatbox2__msg--assistant">
            <div className="chatbox2__avatar chatbox2__avatar--assistant">
              <RobotOutlined />
            </div>
            <div className="chatbox2__bubble chatbox2__bubble--assistant chatbox2__bubble--typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chatbox2__input-wrap">
        <Input.TextArea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Nhập câu hỏi... (Enter để gửi, Shift+Enter xuống dòng)"
          autoSize={{ minRows: 1, maxRows: 4 }}
          className="chatbox2__input"
          disabled={loading}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={submit}
          loading={loading}
          className="chatbox2__send-btn"
          disabled={!value.trim()}
        />
      </div>
    </div>
  );
}
