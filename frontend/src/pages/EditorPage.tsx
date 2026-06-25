import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, WritingPlan, ReviewResult } from "../api/client";
import { useSettingsStore } from "../store/settings";

type SaveStatus = "idle" | "unsaved" | "saving" | "saved" | "error";
type Phase = "idle" | "plan" | "review" | "done";

interface AgentEvent {
  step: string;
  status: string;
  message: string;
  tool?: string;
  final_content?: string;
  input?: string;
}

const EMPTY_PLAN: WritingPlan = {
  involved_characters: [],
  involved_settings: [],
  prev_recap: "",
  this_goal: "",
  next_setup: "",
  beats: [],
};

export default function EditorPage() {
  const { novelId, sectionId } = useParams<{ novelId: string; sectionId: string }>();
  const navigate = useNavigate();
  const settings = useSettingsStore((s) => s.settings);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<AgentEvent[]>([]);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [instruction, setInstruction] = useState("请根据本节大纲概要统筹并创作正文");
  const [styleId, setStyleId] = useState("");
  const [styles, setStyles] = useState<{ id: string; name: string }[]>([]);

  const [phase, setPhase] = useState<Phase>("idle");
  const [threadId, setThreadId] = useState("");
  const [plan, setPlan] = useState<WritingPlan>(EMPTY_PLAN);
  const [reviewDraft, setReviewDraft] = useState("");
  const [review, setReview] = useState<ReviewResult | null>(null);

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
      api.styles.list(novelId).then(setStyles);
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

  const llmParams = {
    api_key: settings.apiKey,
    model: settings.model,
    base_url: settings.baseUrl,
    temperature: settings.temperature,
    max_tokens: settings.maxTokens,
  };

  const onEvent = (raw: Record<string, unknown>) => {
    const evt = raw as unknown as AgentEvent;
    setLogs((prev) => [...prev, evt]);
    if (evt.step === "await_plan") {
      setThreadId((raw.thread_id as string) || "");
      setPlan({ ...EMPTY_PLAN, ...((raw.plan as WritingPlan) || {}) });
      setPhase("plan");
    } else if (evt.step === "await_review") {
      if (raw.thread_id) setThreadId(raw.thread_id as string);
      setReviewDraft((raw.draft as string) || "");
      setReview((raw.review as ReviewResult) || { ok: true, issues: [] });
      setPhase("review");
    } else if (evt.step === "complete") {
      if (evt.final_content) handleChange(evt.final_content);
      setPhase("done");
    }
  };

  const requireKey = () => {
    if (!settings.apiKey) {
      alert("请先在「模型设置」中配置 API Key");
      return false;
    }
    return true;
  };

  const startPlan = async () => {
    if (!requireKey()) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    if (contentRef.current) await doSave(contentRef.current);
    setLoading(true);
    setLogs([]);
    setPhase("idle");
    setReview(null);
    try {
      await api.agent.planStream(novelId, { section_id: sectionId, ...llmParams, instruction, style_id: styleId || undefined }, onEvent);
    } catch (e: any) {
      setLogs((prev) => [...prev, { step: "error", status: "error", message: e.message }]);
    } finally {
      setLoading(false);
    }
  };

  const resume = async (action: "confirm_plan" | "revise" | "polish") => {
    if (!requireKey() || !threadId) return;
    setLoading(true);
    try {
      await api.agent.resumeStream(
        novelId,
        {
          thread_id: threadId,
          action,
          ...llmParams,
          edited_plan: action === "confirm_plan" ? (plan as unknown as Record<string, unknown>) : null,
          edited_draft: action === "confirm_plan" ? null : reviewDraft,
        },
        onEvent,
      );
    } catch (e: any) {
      setLogs((prev) => [...prev, { step: "error", status: "error", message: e.message }]);
    } finally {
      setLoading(false);
    }
  };

  const runSummarize = async () => {
    if (!requireKey()) return;
    if (!contentRef.current.trim()) { alert("正文为空，无法生成摘要"); return; }
    if (timerRef.current) clearTimeout(timerRef.current);
    await doSave(contentRef.current);
    setLoading(true);
    setLogs([]);
    try {
      const res = await api.agent.summarize(novelId, { section_id: sectionId, api_key: settings.apiKey, model: settings.model, base_url: settings.baseUrl, content: contentRef.current });
      setLogs([{ step: "summary", status: "done", message: "摘要完成", final_content: res.summary }]);
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
    if (evt.status === "await") return "#8b5cf6";
    if (evt.step === "complete" || evt.status === "done") return "#22c55e";
    return "var(--text-secondary)";
  };

  const STEP_LABELS: Record<string, string> = {
    init: "初始化", plan: "统筹计划", write: "写作", review: "审查", revise: "修订",
    polish: "润色", save: "保存", complete: "完成", error: "错误", summary: "摘要",
    resume: "继续", await_plan: "等待确认计划", await_review: "等待选择",
  };

  const updatePlan = (patch: Partial<WritingPlan>) => setPlan((p) => ({ ...p, ...patch }));

  return (
    <div className="editor-container">
      <div className="editor-main">
        <div style={{ marginBottom: 12, display: "flex", gap: 8, alignItems: "center" }}>
          <h2 style={{ fontSize: 16 }}>写作：{sectionId}</h2>
          <button className="btn btn-primary btn-sm" onClick={manualSave}>保存</button>
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
        <h3>写作流水线</h3>

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>创作指令</label>
          <textarea value={instruction} onChange={(e) => setInstruction(e.target.value)} rows={2} style={{ fontSize: 13, resize: "vertical" }} />
        </div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>文风</label>
          <div style={{ display: "flex", gap: 6 }}>
            <select value={styleId} onChange={(e) => setStyleId(e.target.value)} style={{ flex: 1, fontSize: 13 }}>
              <option value="">不使用文风</option>
              {styles.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <button className="btn btn-sm" onClick={() => navigate(`/novel/${novelId}/styles`)} style={{ fontSize: 12 }}>管理</button>
          </div>
        </div>

        {loading && <p style={{ color: "#f59e0b", fontSize: 12 }}>执行中...</p>}

        <button className="agent-btn" onClick={startPlan} disabled={loading}>
          <div className="agent-name">① 生成计划</div>
          <div className="agent-desc">统筹角色/设定/前中后文 → 写作 → 审查 → 润色</div>
        </button>

        {phase === "plan" && (
          <div className="card" style={{ marginTop: 12 }}>
            <h4 style={{ marginTop: 0, fontSize: 13 }}>② 本节计划（可编辑）</h4>
            <div className="form-group">
              <label>出场角色（逗号分隔）</label>
              <input value={plan.involved_characters.join(", ")} onChange={(e) => updatePlan({ involved_characters: e.target.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean) })} />
            </div>
            <div className="form-group">
              <label>用到的设定（逗号分隔）</label>
              <input value={plan.involved_settings.join(", ")} onChange={(e) => updatePlan({ involved_settings: e.target.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean) })} />
            </div>
            <div className="form-group">
              <label>前文回顾</label>
              <textarea value={plan.prev_recap} onChange={(e) => updatePlan({ prev_recap: e.target.value })} rows={2} />
            </div>
            <div className="form-group">
              <label>本节目标</label>
              <textarea value={plan.this_goal} onChange={(e) => updatePlan({ this_goal: e.target.value })} rows={2} />
            </div>
            <div className="form-group">
              <label>为后文铺垫</label>
              <textarea value={plan.next_setup} onChange={(e) => updatePlan({ next_setup: e.target.value })} rows={2} />
            </div>
            <div className="form-group">
              <label>情节节拍（每行一条）</label>
              <textarea value={plan.beats.join("\n")} onChange={(e) => updatePlan({ beats: e.target.value.split("\n").map((s) => s.trim()).filter(Boolean) })} rows={3} />
            </div>
            <button className="btn btn-primary" onClick={() => resume("confirm_plan")} disabled={loading}>确认并写作 →</button>
          </div>
        )}

        {phase === "review" && (
          <div className="card" style={{ marginTop: 12 }}>
            <h4 style={{ marginTop: 0, fontSize: 13 }}>③ 草稿与审查</h4>
            {review && (
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 12, color: review.ok ? "#22c55e" : "#f59e0b", marginBottom: 4 }}>
                  {review.issues.length === 0 ? "审查无问题" : `审查发现 ${review.issues.length} 个问题：`}
                </div>
                {review.issues.map((it, i) => (
                  <div key={i} style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 2 }}>
                    [{it.severity}] {it.type}：{it.description}
                    {it.suggestion && <span style={{ color: "var(--text-muted)" }}>（建议：{it.suggestion}）</span>}
                  </div>
                ))}
              </div>
            )}
            <div className="form-group">
              <label>草稿（可编辑后再修订/润色）</label>
              <textarea value={reviewDraft} onChange={(e) => setReviewDraft(e.target.value)} rows={10} style={{ fontSize: 13 }} />
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-secondary" onClick={() => resume("revise")} disabled={loading}>继续修订</button>
              <button className="btn btn-primary" onClick={() => resume("polish")} disabled={loading}>直接润色 →</button>
            </div>
          </div>
        )}

        <hr style={{ border: "none", borderTop: "1px solid var(--border-light)", margin: "12px 0" }} />

        <button className="agent-btn" onClick={runSummarize} disabled={loading} style={{ borderColor: "#8b5cf6" }}>
          <div className="agent-name" style={{ color: "#8b5cf6" }}>生成摘要</div>
          <div className="agent-desc">归纳正文，更新节描述，标记完成</div>
        </button>

        {logs.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: "var(--text)" }}>执行日志</h4>
            <div style={{ fontSize: 12, maxHeight: 240, overflowY: "auto" }}>
              {logs.map((evt, i) => (
                <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid var(--border-light)", color: getEventColor(evt) }}>
                  <strong>{STEP_LABELS[evt.step] || evt.step}</strong>
                  <span style={{ marginLeft: 4, color: "var(--text-secondary)" }}>{evt.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
