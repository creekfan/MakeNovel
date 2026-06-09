"use client";

import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Trash2, Loader2 } from "lucide-react";
import { useSettingsStore } from "@/store";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function AIChat() {
  const settings = useSettingsStore();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamed, setStreamed] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streamed]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");

    const userMsg: Message = { role: "user", content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setStreaming(true);
    setStreamed("");

    try {
      const payload = {
        messages: updatedMessages.map((m) => ({ role: m.role, content: m.content })),
        provider: settings.provider,
        model: settings.provider === "openai" ? settings.openaiModel
             : settings.provider === "anthropic" ? settings.anthropicModel
             : settings.provider === "deepseek" ? settings.deepseekModel
             : settings.provider === "ollama" ? settings.ollamaModel
             : "",
        api_key: settings.provider === "openai" ? settings.openaiKey
             : settings.provider === "anthropic" ? settings.anthropicKey
             : settings.provider === "deepseek" ? settings.deepseekKey
             : settings.provider === "ollama" ? settings.ollamaUrl
             : "",
      };

      const response = await fetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) return;

      let full = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6).trim();
            if (data === "[DONE]") break;
            try {
              const parsed = JSON.parse(data);
              full += parsed.token || "";
              setStreamed(full);
            } catch {}
          }
        }
      }

      if (full) {
        setMessages([...updatedMessages, { role: "assistant", content: full }]);
      }
    } catch (e) {
      setMessages([...updatedMessages, { role: "assistant", content: `[出错: ${(e as Error).message}]` }]);
    }
    setStreaming(false);
    setStreamed("");
  };

  const handleClear = () => {
    setMessages([]);
    setStreamed("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(!open)}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all cursor-pointer ${
          open
            ? "bg-zinc-700 dark:bg-zinc-300 rotate-90"
            : "bg-indigo-600 hover:bg-indigo-700 hover:scale-110"
        }`}
      >
        {open ? <X size={22} className="text-white dark:text-zinc-900" /> : <MessageCircle size={22} className="text-white" />}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-96 h-[520px] bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl border border-zinc-200 dark:border-zinc-700 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
            <div className="flex items-center gap-2">
              <MessageCircle size={18} className="text-indigo-600" />
              <span className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">AI 写作伙伴</span>
            </div>
            <button
              onClick={handleClear}
              disabled={messages.length === 0 && !streamed}
              className="p-1.5 text-zinc-400 hover:text-red-500 disabled:opacity-30 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
              title="清空对话"
            >
              <Trash2 size={14} />
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-auto p-4 space-y-4">
            {messages.length === 0 && !streamed && (
              <div className="text-center text-sm text-zinc-400 mt-8">
                <MessageCircle size={28} className="mx-auto mb-2 opacity-40" />
                <p>有什么写作问题可以问我</p>
                <p className="text-xs mt-1">比如：情节走向、角色设计、文笔建议…</p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === "user"
                      ? "bg-indigo-600 text-white rounded-br-md"
                      : "bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 rounded-bl-md"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {streaming && streamed && (
              <div className="flex justify-start">
                <div className="max-w-[85%] px-3 py-2 rounded-2xl rounded-bl-md text-sm leading-relaxed bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200">
                  {streamed}
                  <span className="inline-block w-1.5 h-4 bg-indigo-500 ml-0.5 animate-pulse align-middle" />
                </div>
              </div>
            )}

            {streaming && !streamed && (
              <div className="flex justify-start">
                <div className="px-3 py-2 bg-zinc-100 dark:bg-zinc-800 rounded-2xl rounded-bl-md">
                  <Loader2 size={16} className="animate-spin text-zinc-400" />
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-3 border-t border-zinc-200 dark:border-zinc-800">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入问题..."
                disabled={streaming}
                className="flex-1 px-3 py-2 text-sm border border-zinc-200 dark:border-zinc-700 rounded-xl bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || streaming}
                className="p-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition-colors cursor-pointer shrink-0"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
