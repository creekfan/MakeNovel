import { useState, useRef, useEffect, useCallback } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function OutlineAssistant({
  messages,
  onSend,
  onClose,
  onReset,
  loading,
}: {
  messages: Message[];
  onSend: (text: string) => void;
  onClose: () => void;
  onReset: () => void;
  loading: boolean;
}) {
  const [input, setInput] = useState("");
  const [pos, setPos] = useState({ x: 100, y: 60 });
  const dragRef = useRef({ active: false, startX: 0, startY: 0, posX: 0, posY: 0 });
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const onDragStart = useCallback((e: React.MouseEvent) => {
    dragRef.current = { active: true, startX: e.clientX, startY: e.clientY, posX: pos.x, posY: pos.y };
    e.preventDefault();
  }, [pos]);

  useEffect(() => {
    const move = (e: MouseEvent) => {
      if (!dragRef.current.active) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      setPos({ x: dragRef.current.posX + dx, y: dragRef.current.posY + dy });
    };
    const up = () => { dragRef.current.active = false; };
    document.addEventListener("mousemove", move);
    document.addEventListener("mouseup", up);
    return () => {
      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);
    };
  }, []);

  const send = () => {
    const t = input.trim();
    if (!t || loading) return;
    setInput("");
    onSend(t);
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        left: pos.x,
        top: pos.y,
        width: 440,
        minWidth: 360,
        minHeight: 300,
        maxWidth: "90vw",
        maxHeight: "80vh",
        resize: "both",
        overflow: "hidden",
        background: "var(--bg-card, #fff)",
        border: "2px solid var(--border, #ddd)",
        borderRadius: 12,
        boxShadow: "0 8px 32px rgba(0,0,0,0.25)",
        display: "flex",
        flexDirection: "column",
        zIndex: 9999,
      }}
    >
      <div
        onMouseDown={onDragStart}
        style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "8px 14px", borderBottom: "1px solid var(--border-light, #eee)",
          background: "var(--bg-secondary, #f7f8fa)", cursor: "move",
          borderRadius: "10px 10px 0 0", userSelect: "none",
        }}
        title="拖拽移动窗口"
      >
        <strong style={{ fontSize: 14 }}>⠿ 大纲助手</strong>
        <div style={{ display: "flex", gap: 4 }}>
          <button className="btn btn-sm"
            onMouseDown={(e) => e.stopPropagation()}
            onClick={onReset}
            style={{ fontSize: 11 }}
            title="清除对话记忆"
          >
            重置
          </button>
          <button className="btn btn-sm"
            onMouseDown={(e) => e.stopPropagation()}
            onClick={onClose}
            style={{ fontSize: 16, lineHeight: 1 }}
          >
            ✕
          </button>
        </div>
      </div>

      <div style={{ flex: 1, padding: 12, overflowY: "auto" }}>
        {messages.length === 0 && (
          <p style={{ color: "#999", fontSize: 13 }}>
            告诉我你想构思的情节、矛盾点或结构问题，我会基于「矛盾铺设与解决」方法论给出建议。
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            style={{ marginBottom: 10, textAlign: m.role === "user" ? "right" : "left" }}
          >
            <div
              style={{
                display: "inline-block", maxWidth: "85%", borderRadius: 10, padding: "6px 12px",
                fontSize: 13, whiteSpace: "pre-wrap",
                background: m.role === "user" ? "#3b82f6" : "var(--bg-secondary, #f0f0f0)",
                color: m.role === "user" ? "#fff" : "var(--text, #1f2937)",
              }}
            >
              {m.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div style={{ padding: 8, borderTop: "1px solid var(--border-light, #eee)", display: "flex", gap: 6 }}>
        <input
          style={{ flex: 1, fontSize: 13, marginBottom: 0 }}
          placeholder="输入你的问题..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
          disabled={loading}
        />
        <button className="btn btn-primary btn-sm" onClick={send} disabled={loading}>
          {loading ? "..." : "发送"}
        </button>
      </div>
    </div>
  );
}
