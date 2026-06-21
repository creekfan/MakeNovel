import { useEffect, useState, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { useSettingsStore } from "../store/settings";

type SaveStatus = "idle" | "unsaved" | "saving" | "saved" | "error";

interface AgentEvent {
  step: string;
  status: string;
  message: string;
  tool?: string;
  final_content?: string;
  input?: string;
}

export default function EditorPage() {
  const { novelId, sectionId } = useParams<{ novelId: string; sectionId: string }>();
  const settings = useSettingsStore((s) => s.settings);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<AgentEvent[]>([]);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [instruction, setInstruction] = useState("请根据大纲概要创作本节正文");
  const loaded = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const contentRef = useRef("");

  useEffect(() => {
    loaded.current = false;
    if (novelId && sectionId) {
      api.outline.getContent(novelId, sectionId).then((res) => {
        const c = res.content || "";
        setContent(c);
        contentRef.current = c;
        loaded.current = true;
        setSaveStatus("idle");
      });
    }
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [novelId, sectionId]);

  const doSave = useCallback(async (text: string) => {
    if (!novelId || !sectionId) return;
    setSaveStatus("saving");
    try {
      await api.outline.saveContent(novelId, sectionId, text);
      setSaveStatus("saved");
    } catch {
      setSaveStatus("error");
    }
  }, [novelId, sectionId]);

  const handleChange = (text: string) => {
    setContent(text);
    contentRef.current = text;
    if (!loaded.current) return;
    setSaveStatus("unsaved");
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSave(text), 1000);
  };

  const manualSave = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    doSave(contentRef.current);
  };

  if (!novelId || !sectionId) return null;

  const runAgent = async () => {
    if (!settings.apiKey) {
      alert("请先在「模型设置」中配置 API Key");
      return;
    }
    if (timerRef.current) clearTimeout(timerRef.current);
    if (contentRef.current) await doSave(contentRef.current);

    setLoading(true);
    setLogs([]);

    try {
      await api.agent.runAgentStream(
        novelId,
        {
          section_id: sectionId,
          api_key: settings.apiKey,
          model: settings.model,
          base_url: settings.baseUrl,
          temperature: settings.temperature,
          max_tokens: settings.maxTokens,
          instruction: instruction,
        },
        (event) => {
          const evt = event as unknown as AgentEvent;
          if (evt.step === "complete") {
            if (evt.final_content) {
              handleChange(evt.final_content);
            }
          }
          setLogs((prev) => [...prev, evt]);
        },
      );
    } catch (e: any) {
      setLogs((prev) => [...prev, { step: "error", status: "error", message: e.message }]);
    } finally {
      setLoading(false);
    }
  };

  const runSummarize = async () => {
    if (!settings.apiKey) {
      alert("请先在「模型设置」中配置 API Key");
      return;
    }
    if (!contentRef.current.trim()) {
      alert("正文为空，无法生成摘要");
      return;
    }
    if (timerRef.current) clearTimeout(timerRef.current);
    await doSave(contentRef.current);

    setLoading(true);
    setLogs([]);
    try {
      const res = await api.agent.summarize(novelId, {
        section_id: sectionId,
        api_key: settings.apiKey,
        model: settings.model,
        base_url: settings.baseUrl,
        content: contentRef.current,
      });
      setLogs([
        { step: "summary", status: "done", message: "摘要完成", final_content: res.summary },
      ]);
    } catch (e: any) {
      setLogs([{ step: "error", status: "error", message: `错误: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const statusLabel: Record<SaveStatus, { text: string; color: string }> = {
    idle: { text: "", color: "transparent" },
    unsaved: { text: "未保存", color: "#f59e0b" },
    saving: { text: "保存中...", color: "#3b82f6" },
    saved: { text: "已保存", color: "#22c55e" },
    error: { text: "保存失败", color: "#ef4444" },
  };

  const getEventColor = (evt: AgentEvent) => {
    if (evt.status === "error") return "#ef4444";
    if (evt.status === "running") return "#f59e0b";
    if (evt.step === "complete" || evt.status === "done") return "#22c55e";
    return "var(--text-secondary)";
  };

  const getEventIcon = (evt: AgentEvent) => {
    if (evt.status === "running") return "⟳";
    if (evt.status === "done") return "✓";
    if (evt.status === "error") return "✕";
    return "○";
  };

  const getEventLabel = (evt: AgentEvent) => {
    if (evt.step === "init") return "初始化";
    if (evt.step === "thinking") return "思考";
    if (evt.step === "tool_call") return `工具: ${evt.tool || ""}`;
    if (evt.step === "complete") return "完成";
    if (evt.step === "error") return "错误";
    if (evt.step === "summary") return "摘要";
    return evt.step;
  };

  return (
    <div className="editor-container">
      <div className="editor-main">
        <div style={{ marginBottom: 12, display: "flex", gap: 8, alignItems: "center" }}>
          <h2 style={{ fontSize: 16 }}>写作：{sectionId}</h2>
          <button className="btn btn-primary btn-sm" onClick={manualSave}>
            保存
          </button>
          {saveStatus !== "idle" && (
            <span style={{ fontSize: 12, color: statusLabel[saveStatus].color, fontWeight: 500 }}>
              {statusLabel[saveStatus].text}
            </span>
          )}
        </div>
        <textarea
          value={content}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="在此编写正文..."
          disabled={loading}
        />
      </div>
      <div className="agent-panel">
        <h3>LangChain Agent</h3>

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
            创作指令
          </label>
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={3}
            style={{ fontSize: 13, resize: "vertical" }}
            placeholder="告诉 Agent 要做什么..."
          />
        </div>

        {loading && <p style={{ color: "#f59e0b", fontSize: 12 }}>Agent 执行中...</p>}

        <button className="agent-btn" onClick={runAgent} disabled={loading}>
          <div className="agent-name">运行 Agent</div>
          <div className="agent-desc">LangChain ReAct：自动获取上下文 → 创作 → 审查 → 润色</div>
        </button>

        <hr style={{ border: "none", borderTop: "1px solid var(--border-light)", margin: "12px 0" }} />

        <button className="agent-btn" onClick={runSummarize} disabled={loading} style={{ borderColor: "#8b5cf6" }}>
          <div className="agent-name" style={{ color: "#8b5cf6" }}>生成摘要</div>
          <div className="agent-desc">归纳正文，更新节描述，标记完成</div>
        </button>

        {logs.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: "var(--text)" }}>执行日志</h4>
            <div style={{ fontSize: 12, maxHeight: 300, overflowY: "auto" }}>
              {logs.map((evt, i) => (
                <div key={i} style={{
                  padding: "4px 0",
                  borderBottom: "1px solid var(--border-light)",
                  color: getEventColor(evt),
                }}>
                  <span style={{ marginRight: 4 }}>{getEventIcon(evt)}</span>
                  <strong>{getEventLabel(evt)}</strong>
                  <span style={{ marginLeft: 4, color: "var(--text-secondary)" }}>{evt.message}</span>
                  {evt.input && (
                    <div style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 16, whiteSpace: "pre-wrap" }}>
                      {evt.input}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
