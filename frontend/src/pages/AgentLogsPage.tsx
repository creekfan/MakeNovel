import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, AgentLogSummary, AgentLog, AgentLogEvent } from "../api/client";

function fmtTime(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

const STATUS_COLOR: Record<string, string> = {
  done: "#22c55e",
  error: "#ef4444",
  running: "#3b82f6",
};

function EventRow({ ev }: { ev: AgentLogEvent }) {
  const color =
    ev.status === "error" ? "#ef4444" : ev.status === "done" ? "#22c55e" : "#3b82f6";
  return (
    <div style={{ borderLeft: `3px solid ${color}`, paddingLeft: 8, marginBottom: 6 }}>
      <div style={{ fontSize: 12 }}>
        <span style={{ fontWeight: 600 }}>{ev.step}</span>
        {ev.tool && <span className="tag" style={{ marginLeft: 6 }}>{ev.tool}</span>}
        <span style={{ marginLeft: 6, color: "#888" }}>{ev.status}</span>
      </div>
      {ev.message && <div style={{ fontSize: 12, color: "#555" }}>{ev.message}</div>}
      {ev.input && (
        <div style={{ fontSize: 11, color: "#777", whiteSpace: "pre-wrap" }}>入参: {ev.input}</div>
      )}
      {ev.output && (
        <div style={{ fontSize: 11, color: "#777", whiteSpace: "pre-wrap" }}>结果: {ev.output}</div>
      )}
    </div>
  );
}

export default function AgentLogsPage() {
  const { novelId } = useParams<{ novelId: string }>();
  const [logs, setLogs] = useState<AgentLogSummary[]>([]);
  const [selected, setSelected] = useState<AgentLog | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = () => {
    if (novelId) api.agent.logs.list(novelId).then(setLogs);
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [novelId]);

  if (!novelId) return null;

  const open = async (runId: string) => {
    setLoading(true);
    try {
      const log = await api.agent.logs.get(novelId, runId);
      setSelected(log);
    } finally {
      setLoading(false);
    }
  };

  const remove = async (runId: string) => {
    await api.agent.logs.delete(novelId, runId);
    if (selected?.run_id === runId) setSelected(null);
    refresh();
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <h2>运行日志（LangGraph）</h2>
        <button className="btn btn-secondary" onClick={refresh}>刷新</button>
      </div>

      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: "0 0 360px" }}>
          {logs.length === 0 && <p style={{ color: "#999" }}>暂无运行记录。运行一次写作 Agent 后会自动记录。</p>}
          {logs.map((l) => (
            <div
              key={l.run_id}
              className="card"
              style={{
                marginBottom: 8,
                cursor: "pointer",
                borderColor: selected?.run_id === l.run_id ? "#3b82f6" : undefined,
              }}
              onClick={() => open(l.run_id)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong style={{ fontSize: 13 }}>{l.section_title || l.section_id}</strong>
                <span style={{ fontSize: 11, color: STATUS_COLOR[l.status] || "#888", fontWeight: 600 }}>
                  {l.status}
                </span>
              </div>
              <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>{fmtTime(l.started_at)}</div>
              <div style={{ fontSize: 11, color: "#888" }}>
                {l.model} · {l.event_count} 事件 · {l.final_len} 字
              </div>
              <button
                className="btn btn-danger btn-sm"
                style={{ marginTop: 6 }}
                onClick={(e) => {
                  e.stopPropagation();
                  remove(l.run_id);
                }}
              >
                删除
              </button>
            </div>
          ))}
        </div>

        <div style={{ flex: 1 }}>
          {loading && <p>加载中...</p>}
          {!loading && !selected && <p style={{ color: "#999" }}>选择左侧一条记录查看详情</p>}
          {!loading && selected && (
            <div className="card">
              <h3 style={{ marginTop: 0, fontSize: 15 }}>
                {selected.section_title || selected.section_id}
              </h3>
              <div style={{ fontSize: 12, color: "#666", marginBottom: 4 }}>
                指令：{selected.instruction || "（无）"}
              </div>
              <div style={{ fontSize: 12, color: "#888", marginBottom: 12 }}>
                {selected.model} · 开始 {fmtTime(selected.started_at)} · 结束 {fmtTime(selected.finished_at)} ·{" "}
                <span style={{ color: STATUS_COLOR[selected.status] || "#888" }}>{selected.status}</span>
              </div>

              <h4 style={{ fontSize: 13, marginBottom: 8 }}>事件流（{selected.events.length}）</h4>
              <div style={{ maxHeight: 360, overflow: "auto", marginBottom: 12 }}>
                {selected.events.map((ev, i) => (
                  <EventRow key={i} ev={ev} />
                ))}
              </div>

              {selected.final_content && (
                <>
                  <h4 style={{ fontSize: 13, marginBottom: 6 }}>最终正文（{selected.final_content.length} 字）</h4>
                  <div
                    style={{
                      fontSize: 13,
                      whiteSpace: "pre-wrap",
                      background: "rgba(0,0,0,0.03)",
                      padding: 10,
                      borderRadius: 6,
                      maxHeight: 300,
                      overflow: "auto",
                    }}
                  >
                    {selected.final_content}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
