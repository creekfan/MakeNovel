import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, OutlineTree, OutlineNode } from "../api/client";

function generateId() {
  return "node-" + Math.random().toString(36).slice(2, 10);
}

function NodeItem({
  node,
  onUpdate,
  onDelete,
  onNavigate,
  onInsertAfter,
}: {
  node: OutlineNode;
  onUpdate: (updated: OutlineNode) => void;
  onDelete: () => void;
  onNavigate: (sectionId: string) => void;
  onInsertAfter: () => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(node.title);
  const [summary, setSummary] = useState(node.summary);

  useEffect(() => {
    setTitle(node.title);
    setSummary(node.summary);
  }, [node.title, node.summary]);

  const badgeClass =
    node.node_type === "volume"
      ? "badge-volume"
      : node.node_type === "chapter"
      ? "badge-chapter"
      : "badge-section";

  const typeLabel =
    node.node_type === "volume" ? "卷" : node.node_type === "chapter" ? "章" : "节";

  const addChild = () => {
    const childType =
      node.node_type === "volume" ? "chapter" : "section";
    const newChild: OutlineNode = {
      id: generateId(),
      title: `新${childType === "chapter" ? "章" : "节"}`,
      node_type: childType,
      summary: "",
      status: "planned",
      children: [],
      sort_order: node.children.length + 1,
    };
    onUpdate({ ...node, children: [...node.children, newChild] });
  };

  const saveEdit = () => {
    onUpdate({ ...node, title, summary });
    setEditing(false);
  };

  const updateChild = (idx: number, updated: OutlineNode) => {
    const newChildren = [...node.children];
    newChildren[idx] = updated;
    onUpdate({ ...node, children: newChildren });
  };

  const deleteChild = (idx: number) => {
    onUpdate({ ...node, children: node.children.filter((_, i) => i !== idx) });
  };

  const insertChildAfter = (idx: number) => {
    const ref = node.children[idx];
    const next = node.children[idx + 1];
    const newOrder = next
      ? (ref.sort_order + next.sort_order) / 2
      : ref.sort_order + 1;
    const newChild: OutlineNode = {
      id: generateId(),
      title: `新${ref.node_type === "chapter" ? "章" : "节"}`,
      node_type: ref.node_type,
      summary: "",
      status: "planned",
      children: [],
      sort_order: newOrder,
    };
    const newChildren = [...node.children];
    newChildren.splice(idx + 1, 0, newChild);
    onUpdate({ ...node, children: newChildren });
  };

  return (
    <div className="node">
      <div className="node-header" onClick={() => setExpanded(!expanded)}>
        <span className={`node-type-badge ${badgeClass}`}>{typeLabel}</span>
        {editing ? (
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            style={{ marginBottom: 0, width: 200 }}
          />
        ) : (
          <span style={{ fontWeight: 500 }}>{node.title}</span>
        )}
        <span className={`status-${node.status}`} style={{ fontSize: 12 }}>
          [{node.status}]
        </span>
        {node.node_type === "section" && (
          <button
            className="btn btn-primary btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              onNavigate(node.id);
            }}
          >
            写作
          </button>
        )}
        <button
          className="btn btn-secondary btn-sm"
          onClick={(e) => {
            e.stopPropagation();
            if (editing) {
              setTitle(node.title);
              setSummary(node.summary);
              setEditing(false);
            } else {
              setTitle(node.title);
              setSummary(node.summary);
              setEditing(true);
            }
          }}
        >
          {editing ? "取消" : "编辑"}
        </button>
        {node.node_type !== "section" && (
          <button
            className="btn btn-success btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              addChild();
            }}
          >
            +子节点
          </button>
        )}
        <button
          className="btn btn-danger btn-sm"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
        >
          删除
        </button>
        <button
          className="btn btn-sm"
          style={{ background: "#8b5cf6", color: "#fff" }}
          onClick={(e) => {
            e.stopPropagation();
            onInsertAfter();
          }}
          title="在此节点后插入同级节点"
        >
          ↓+
        </button>
      </div>
      {editing && (
        <div style={{ marginLeft: 32, padding: "8px 0" }}>
          <textarea
            placeholder="情节概要..."
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            rows={2}
          />
          <button className="btn btn-primary btn-sm" onClick={saveEdit}>
            确认
          </button>
        </div>
      )}
      {expanded && node.children.length > 0 && (
        <div>
          {node.children.map((child, idx) => (
            <NodeItem
              key={child.id}
              node={child}
              onUpdate={(u) => updateChild(idx, u)}
              onDelete={() => deleteChild(idx)}
              onNavigate={onNavigate}
              onInsertAfter={() => insertChildAfter(idx)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

type SaveStatus = "idle" | "unsaved" | "saving" | "saved" | "error";

export default function OutlinePage() {
  const { novelId } = useParams<{ novelId: string }>();
  const navigate = useNavigate();
  const [outline, setOutline] = useState<OutlineTree | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const loaded = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (novelId) {
      api.outline.get(novelId).then((data) => {
        setOutline(data);
        loaded.current = true;
        setSaveStatus("idle");
      });
    }
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [novelId]);

  const doSave = useCallback(async (data: OutlineTree) => {
    if (!novelId) return;
    setSaveStatus("saving");
    try {
      await api.outline.save(novelId, data);
      setSaveStatus("saved");
    } catch {
      setSaveStatus("error");
    }
  }, [novelId]);

  const scheduleAutoSave = useCallback((data: OutlineTree) => {
    if (!loaded.current) return;
    setSaveStatus("unsaved");
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSave(data), 800);
  }, [doSave]);

  if (!outline || !novelId) return <div>加载中...</div>;

  const updateOutline = (next: OutlineTree) => {
    setOutline(next);
    scheduleAutoSave(next);
  };

  const addVolume = () => {
    const newVol: OutlineNode = {
      id: generateId(),
      title: "新卷",
      node_type: "volume",
      summary: "",
      status: "planned",
      children: [],
      sort_order: outline.volumes.length + 1,
    };
    updateOutline({ ...outline, volumes: [...outline.volumes, newVol] });
  };

  const updateVolume = (idx: number, updated: OutlineNode) => {
    const vols = [...outline.volumes];
    vols[idx] = updated;
    updateOutline({ ...outline, volumes: vols });
  };

  const deleteVolume = (idx: number) => {
    updateOutline({ ...outline, volumes: outline.volumes.filter((_, i) => i !== idx) });
  };

  const insertVolumeAfter = (idx: number) => {
    const ref = outline.volumes[idx];
    const next = outline.volumes[idx + 1];
    const newOrder = next
      ? (ref.sort_order + next.sort_order) / 2
      : ref.sort_order + 1;
    const newVol: OutlineNode = {
      id: generateId(),
      title: "新卷",
      node_type: "volume",
      summary: "",
      status: "planned",
      children: [],
      sort_order: newOrder,
    };
    const vols = [...outline.volumes];
    vols.splice(idx + 1, 0, newVol);
    updateOutline({ ...outline, volumes: vols });
  };

  const manualSave = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    doSave(outline);
  };

  const goToEditor = (sectionId: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    doSave(outline).then(() => navigate(`/novel/${novelId}/editor/${sectionId}`));
  };

  const statusLabel: Record<SaveStatus, { text: string; color: string }> = {
    idle: { text: "", color: "transparent" },
    unsaved: { text: "未保存", color: "#f59e0b" },
    saving: { text: "保存中...", color: "#3b82f6" },
    saved: { text: "已保存", color: "#22c55e" },
    error: { text: "保存失败", color: "#ef4444" },
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h2>大纲目录</h2>
          {saveStatus !== "idle" && (
            <span style={{ fontSize: 12, color: statusLabel[saveStatus].color, fontWeight: 500 }}>
              {statusLabel[saveStatus].text}
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-success" onClick={addVolume}>
            + 新增卷
          </button>
          <button className="btn btn-primary" onClick={manualSave}>
            保存大纲
          </button>
        </div>
      </div>
      <div className="card outline-tree">
        {outline.volumes.length === 0 && <p style={{ color: "#999" }}>暂无大纲，点击"新增卷"开始</p>}
        {outline.volumes.map((vol, idx) => (
          <NodeItem
            key={vol.id}
            node={vol}
            onUpdate={(u) => updateVolume(idx, u)}
            onDelete={() => deleteVolume(idx)}
            onNavigate={goToEditor}
            onInsertAfter={() => insertVolumeAfter(idx)}
          />
        ))}
      </div>
    </div>
  );
}
