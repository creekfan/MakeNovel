import { useEffect, useState, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { useSettingsStore } from "../store/settings";

type SaveStatus = "idle" | "unsaved" | "saving" | "saved" | "error";
type StepStatus = "pending" | "running" | "done" | "skipped" | "error";

interface PipelineStep {
  id: string;
  label: string;
  status: StepStatus;
  message: string;
  detail?: Record<string, unknown>;
}

const INITIAL_STEPS: PipelineStep[] = [
  { id: "preparer", label: "准备者", status: "pending", message: "" },
  { id: "creator", label: "创作者", status: "pending", message: "" },
  { id: "reviewer", label: "审查者", status: "pending", message: "" },
  { id: "reviser", label: "修订者", status: "pending", message: "" },
  { id: "polisher", label: "润色者", status: "pending", message: "" },
];

function StepDetail({ step }: { step: PipelineStep }) {
  const [expanded, setExpanded] = useState(false);
  if (!step.detail || step.status === "pending" || step.status === "running") return null;

  const renderContent = () => {
    const d = step.detail!;
    if (step.id === "preparer") {
      return (
        <div style={{ fontSize: 12, lineHeight: 1.6 }}>
          <div><b>当前节：</b>{String(d.current_section || "")}</div>
          <div><b>起始状态：</b>{String(d.starting_state || "")}</div>
          <div><b>要写什么：</b>{String(d.what_to_write || "")}</div>
          <div><b>终止状态：</b>{String(d.ending_state || "")}</div>
          {Array.isArray(d.involved_characters) && d.involved_characters.length > 0 && (
            <div><b>涉及角色：</b>{(d.involved_characters as string[]).join("、")}</div>
          )}
          {Array.isArray(d.involved_world_settings) && d.involved_world_settings.length > 0 && (
            <div><b>涉及设定：</b>{(d.involved_world_settings as string[]).join("、")}</div>
          )}
          {Array.isArray(d.context_summaries) && d.context_summaries.length > 0 && (
            <div><b>前文摘要：</b>{(d.context_summaries as string[]).join("；")}</div>
          )}
        </div>
      );
    }
    if (step.id === "reviewer") {
      const issues = (d.issues as Array<{type: string; severity: string; description: string; suggestion: string}>) || [];
      return (
        <div style={{ fontSize: 12, lineHeight: 1.6 }}>
          {typeof d.overall === "string" && <div><b>总评：</b>{d.overall}</div>}
          {issues.length === 0 && <div style={{ color: "#22c55e" }}>未发现问题</div>}
          {issues.map((issue, i) => (
            <div key={i} style={{ marginTop: 4, paddingLeft: 8, borderLeft: "2px solid var(--border)" }}>
              <span style={{ color: issue.severity === "critical" ? "#ef4444" : "#f59e0b" }}>[{issue.severity}]</span>{" "}
              <span style={{ color: "var(--text-secondary)" }}>{issue.type}</span>：{issue.description}
              {issue.suggestion && <div style={{ color: "var(--text-muted)", marginTop: 2 }}>建议：{issue.suggestion}</div>}
            </div>
          ))}
        </div>
      );
    }
    if (d.content) {
      const text = d.content as string;
      return (
        <pre style={{ fontSize: 12, whiteSpace: "pre-wrap", lineHeight: 1.6, maxHeight: 200, overflowY: "auto", color: "var(--text-secondary)" }}>
          {text.length > 500 ? text.slice(0, 500) + `\n... (共 ${text.length} 字)` : text}
        </pre>
      );
    }
    return null;
  };

  return (
    <div style={{ marginTop: 4, marginBottom: 4 }}>
      <span
        onClick={() => setExpanded(!expanded)}
        style={{ fontSize: 11, color: "#4a6cf7", cursor: "pointer", userSelect: "none" }}
      >
        {expanded ? "▾ 收起详情" : "▸ 查看详情"}
      </span>
      {expanded && (
        <div style={{ marginTop: 4, padding: 8, background: "var(--bg-hover)", borderRadius: 4 }}>
          {renderContent()}
        </div>
      )}
    </div>
  );
}

function StepIndicator({ step }: { step: PipelineStep }) {
  const icons: Record<StepStatus, string> = {
    pending: "○",
    running: "◉",
    done: "●",
    skipped: "◌",
    error: "✕",
  };
  const colors: Record<StepStatus, string> = {
    pending: "var(--text-muted)",
    running: "#f59e0b",
    done: "#22c55e",
    skipped: "var(--text-muted)",
    error: "#ef4444",
  };
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ color: colors[step.status], fontWeight: 700, fontSize: 14 }}>
          {icons[step.status]}
        </span>
        <div style={{ flex: 1 }}>
          <span style={{ fontSize: 13, fontWeight: step.status === "running" ? 600 : 400, color: "var(--text)" }}>
            {step.label}
          </span>
          {step.status === "running" && <span style={{ marginLeft: 6, color: "#f59e0b", fontSize: 11 }}>进行中...</span>}
          {step.message && step.status !== "running" && (
            <span style={{ marginLeft: 8, fontSize: 11, color: "var(--text-secondary)" }}>{step.message}</span>
          )}
        </div>
      </div>
      <div style={{ marginLeft: 22 }}>
        <StepDetail step={step} />
      </div>
    </div>
  );
}

export default function EditorPage() {
  const { novelId, sectionId } = useParams<{ novelId: string; sectionId: string }>();
  const settings = useSettingsStore((s) => s.settings);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [steps, setSteps] = useState<PipelineStep[]>([]);
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

  const runPipelineStream = async () => {
    if (!settings.apiKey) {
      alert("请先在「模型设置」中配置 API Key");
      return;
    }
    if (timerRef.current) clearTimeout(timerRef.current);
    if (contentRef.current) await doSave(contentRef.current);

    setLoading(true);
    setLogs([]);
    setSteps(INITIAL_STEPS.map((s) => ({ ...s })));

    try {
      await api.agent.runStream(
        novelId,
        {
          section_id: sectionId,
          api_key: settings.apiKey,
          model: settings.model,
          base_url: settings.baseUrl,
          temperature: settings.temperature,
          max_tokens: settings.maxTokens,
        },
        (event) => {
          if (event.step === "complete") {
            if (event.final_content) {
              handleChange(event.final_content);
            }
            setSteps((prev) => prev.map((s) => s.status === "pending" ? { ...s, status: "skipped" } : s));
          } else if (event.step === "error") {
            setLogs((prev) => [...prev, `错误: ${event.message}`]);
          } else {
            setSteps((prev) =>
              prev.map((s) =>
                s.id === event.step
                  ? { ...s, status: event.status as StepStatus, message: event.message, detail: (event as any).detail }
                  : s
              )
            );
          }
        },
      );
    } catch (e: any) {
      setLogs([`错误: ${e.message}`]);
    } finally {
      setLoading(false);
    }
  };

  const runAgent = async (agentName: string) => {
    if (!settings.apiKey) {
      alert("请先在「模型设置」中配置 API Key");
      return;
    }
    if (timerRef.current) clearTimeout(timerRef.current);
    if (contentRef.current) await doSave(contentRef.current);

    setLoading(true);
    setLogs([]);
    setSteps([]);
    try {
      const res = await api.agent.single(novelId, {
        section_id: sectionId,
        api_key: settings.apiKey,
        model: settings.model,
        base_url: settings.baseUrl,
        temperature: settings.temperature,
        max_tokens: settings.maxTokens,
        agent_name: agentName,
        content: contentRef.current || undefined,
      });
      if (typeof res.result === "string") {
        handleChange(res.result);
      }
      setLogs([`[${res.agent}] 执行完成`]);
    } catch (e: any) {
      setLogs([`错误: ${e.message}`]);
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
    setSteps([]);
    try {
      const res = await api.agent.summarize(novelId, {
        section_id: sectionId,
        api_key: settings.apiKey,
        model: settings.model,
        base_url: settings.baseUrl,
        content: contentRef.current,
      });
      const logLines = [
        `[摘要] 生成完成，已更新节描述并标记为 done`,
        `摘要: ${res.summary}`,
      ];
      if (res.key_events.length > 0) {
        logLines.push(`关键事件: ${res.key_events.join("；")}`);
      }
      setLogs(logLines);
    } catch (e: any) {
      setLogs([`错误: ${e.message}`]);
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
        {steps.length > 0 && (
          <div style={{ marginTop: 8, padding: 12, background: "var(--bg-card)", border: "1px solid var(--border-light)", borderRadius: 6 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: "var(--text)" }}>管道进度</div>
            {steps.map((s) => (
              <StepIndicator key={s.id} step={s} />
            ))}
          </div>
        )}
        {logs.length > 0 && (
          <div style={{ marginTop: 8, padding: 12, background: "var(--bg-card)", border: "1px solid var(--border-light)", borderRadius: 6, fontSize: 12, color: "var(--text-secondary)" }}>
            {logs.map((l, i) => (
              <div key={i}>{l}</div>
            ))}
          </div>
        )}
      </div>
      <div className="agent-panel">
        <h3>Agent 快捷操作</h3>
        {loading && <p style={{ color: "#f59e0b", fontSize: 12 }}>正在执行...</p>}
        <button className="agent-btn" onClick={runPipelineStream} disabled={loading}>
          <div className="agent-name">完整管道</div>
          <div className="agent-desc">准备→创作→审查→修订→润色</div>
        </button>
        <button className="agent-btn" onClick={() => runAgent("preparer")} disabled={loading}>
          <div className="agent-name">准备者</div>
          <div className="agent-desc">分析大纲，准备写作材料</div>
        </button>
        <button className="agent-btn" onClick={() => runAgent("creator")} disabled={loading}>
          <div className="agent-name">创作者</div>
          <div className="agent-desc">根据准备材料生成正文</div>
        </button>
        <button className="agent-btn" onClick={() => runAgent("reviewer")} disabled={loading}>
          <div className="agent-name">审查者</div>
          <div className="agent-desc">审查正文逻辑/一致性</div>
        </button>
        <button className="agent-btn" onClick={() => runAgent("polisher")} disabled={loading}>
          <div className="agent-name">润色者</div>
          <div className="agent-desc">优化文笔和表达</div>
        </button>
        <hr style={{ border: "none", borderTop: "1px solid var(--border-light)", margin: "12px 0" }} />
        <button className="agent-btn" onClick={runSummarize} disabled={loading} style={{ borderColor: "#8b5cf6" }}>
          <div className="agent-name" style={{ color: "#8b5cf6" }}>生成摘要</div>
          <div className="agent-desc">归纳正文，替换节描述，标记完成</div>
        </button>
      </div>
    </div>
  );
}
