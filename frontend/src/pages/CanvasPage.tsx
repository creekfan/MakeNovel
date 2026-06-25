import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  ConnectionMode,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
} from "@xyflow/react";
import type { Node, Edge, Connection, NodeProps } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { connectionKind, nextNodePosition } from "./canvasLogic";
import {
  api,
  Snapshot,
  NovelEvent,
  Character,
  WorldSetting,
  CanvasData,
  CanvasEdge,
  SnapshotPlacement,
} from "../api/client";

function genId(prefix: string) {
  return `${prefix}-` + Math.random().toString(36).slice(2, 10);
}

const NOTE_COLORS: Record<string, string> = {
  character: "#fde68a",
  setting: "#bbf7d0",
  free: "#e9d5ff",
};

const HANDLE_STYLE = {
  width: 11,
  height: 11,
  background: "#3b82f6",
  border: "2px solid #fff",
};

const HANDLE_SIDES = [
  { key: "top", pos: Position.Top },
  { key: "right", pos: Position.Right },
  { key: "bottom", pos: Position.Bottom },
  { key: "left", pos: Position.Left },
] as const;

function FourWayHandles() {
  return (
    <>
      {HANDLE_SIDES.map((s) => (
        <Handle key={s.key} id={s.key} type="source" position={s.pos} style={HANDLE_STYLE} />
      ))}
    </>
  );
}

function StickyNoteNode({ data, selected }: NodeProps) {
  const d = data as any;
  return (
    <div
      style={{
        background: NOTE_COLORS[d.sourceType] || NOTE_COLORS.free,
        border: selected ? "2px solid #3b82f6" : "1px solid rgba(0,0,0,0.15)",
        borderRadius: 4,
        padding: "8px 10px",
        width: 180,
        minHeight: 70,
        boxShadow: d.highlight
          ? "0 0 0 3px #ef4444, 2px 4px 8px rgba(0,0,0,0.25)"
          : "2px 4px 8px rgba(0,0,0,0.2)",
        color: "#1f2937",
        fontSize: 12,
      }}
    >
      <FourWayHandles />
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <strong style={{ fontSize: 13 }}>{d.name || "未命名"}</strong>
        <span style={{ fontSize: 10, opacity: 0.6 }}>
          {d.sourceType === "character" ? "角色" : d.sourceType === "setting" ? "设定" : "便签"}
        </span>
      </div>
      {d.label && <div style={{ fontStyle: "italic", opacity: 0.8, marginBottom: 2 }}>{d.label}</div>}
      {d.category && (
        <span
          style={{
            display: "inline-block",
            fontSize: 10,
            background: "rgba(0,0,0,0.12)",
            borderRadius: 8,
            padding: "1px 6px",
            marginBottom: 4,
          }}
        >
          #{d.category}
        </span>
      )}
      <div style={{ whiteSpace: "pre-wrap", maxHeight: 80, overflow: "hidden" }}>{d.summary || ""}</div>
    </div>
  );
}

function EventNode({ data, selected }: NodeProps) {
  const d = data as any;
  return (
    <div
      style={{
        background: "#1e293b",
        color: "#f1f5f9",
        border: selected ? "2px solid #3b82f6" : "1px solid #334155",
        borderRadius: 8,
        padding: "8px 12px",
        width: 200,
        boxShadow: d.highlight ? "0 0 0 3px #ef4444" : "0 2px 6px rgba(0,0,0,0.3)",
        fontSize: 12,
      }}
    >
      <FourWayHandles />
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <strong style={{ fontSize: 13 }}>⚡ {d.title || "事件"}</strong>
        {d.timeLabel && <span style={{ fontSize: 10, opacity: 0.7 }}>{d.timeLabel}</span>}
      </div>
      <div style={{ whiteSpace: "pre-wrap", maxHeight: 80, overflow: "hidden", opacity: 0.9 }}>
        {d.description || ""}
      </div>
    </div>
  );
}

function snapshotSummary(s: Snapshot): string {
  const f = s.fields || {};
  return (
    (f.personality as string) ||
    (f.description as string) ||
    (f.current_state as string) ||
    (f.background as string) ||
    ""
  );
}

function edgeStyleFor(kind: CanvasEdge["kind"]) {
  if (kind === "event_to_note_change") {
    return { stroke: "#ef4444", strokeDasharray: "6 4", strokeWidth: 2 };
  }
  if (kind === "event_to_event") {
    return { stroke: "#64748b", strokeWidth: 2 };
  }
  return { stroke: "#94a3b8", strokeWidth: 1.5 };
}

function edgeKindLabel(kind: CanvasEdge["kind"]) {
  if (kind === "event_to_note_change") return "事件 → 便签（变化）";
  if (kind === "event_to_event") return "事件 → 事件";
  return "便签 → 事件";
}

function CanvasInner() {
  const { novelId, nodeId } = useParams<{ novelId: string; nodeId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const focusId = searchParams.get("focus");
  const rf = useReactFlow();

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [events, setEvents] = useState<NovelEvent[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [world, setWorld] = useState<WorldSetting[]>([]);
  const [picker, setPicker] = useState<null | "note" | "event">(null);
  const [selected, setSelected] = useState<Node | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<Edge | null>(null);
  const [placements, setPlacements] = useState<SnapshotPlacement[]>([]);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");

  const loaded = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const placeSeq = useRef(0);

  const nodeTypes = useMemo(() => ({ sticky: StickyNoteNode, event: EventNode }), []);

  useEffect(() => {
    if (!novelId || !nodeId) return;
    loaded.current = false;
    Promise.all([
      api.canvas.get(novelId, nodeId),
      api.snapshots.list(novelId),
      api.events.list(novelId),
      api.characters.get(novelId),
      api.world.get(novelId),
    ]).then(([canvas, snaps, evs, chars, ws]) => {
      setSnapshots(snaps);
      setEvents(evs);
      setCharacters(chars);
      setWorld(ws);
      const snapMap = new Map(snaps.map((s) => [s.id, s]));
      const evMap = new Map(evs.map((e) => [e.id, e]));
      const rfNodes: Node[] = canvas.nodes.map((p) => {
        if (p.entity_type === "event") {
          const e = evMap.get(p.entity_id);
          return {
            id: p.placement_id,
            type: "event",
            position: { x: p.x, y: p.y },
            data: {
              entityId: p.entity_id,
              title: e?.title || "(已删除事件)",
              description: e?.description || "",
              timeLabel: e?.time_label || "",
              highlight: false,
            },
          };
        }
        const s = snapMap.get(p.entity_id);
        return {
          id: p.placement_id,
          type: "sticky",
          position: { x: p.x, y: p.y },
          data: {
            entityId: p.entity_id,
            sourceType: s?.source_type || "free",
            name: s?.name || "(已删除便签)",
            label: s?.label || "",
            category: s?.category || "",
            summary: s ? snapshotSummary(s) : "",
            highlight: false,
          },
        };
      });
      const rfEdges: Edge[] = canvas.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.source_handle ?? undefined,
        targetHandle: e.target_handle ?? undefined,
        data: { kind: e.kind },
        style: edgeStyleFor(e.kind),
      }));
      setNodes(rfNodes);
      setEdges(rfEdges);
      if (canvas.viewport) {
        rf.setViewport(canvas.viewport);
      }
      placeSeq.current = rfNodes.length;
      loaded.current = true;
      if (focusId) {
        setTimeout(() => {
          const target = rfNodes.find((n) => n.id === focusId);
          if (target) {
            rf.setCenter(target.position.x + 100, target.position.y + 50, { zoom: 1.2, duration: 600 });
            setNodes((nds) =>
              nds.map((n) =>
                n.id === focusId ? { ...n, data: { ...n.data, highlight: true } } : n,
              ),
            );
            setTimeout(() => {
              setNodes((nds) =>
                nds.map((n) =>
                  n.id === focusId ? { ...n, data: { ...n.data, highlight: false } } : n,
                ),
              );
            }, 2500);
          }
        }, 300);
      }
    });
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [novelId, nodeId, focusId]);

  const persist = useCallback(() => {
    if (!novelId || !nodeId || !loaded.current) return;
    setSaveState("saving");
    const data: CanvasData = {
      node_id: nodeId,
      nodes: nodes.map((n) => ({
        placement_id: n.id,
        entity_type: n.type === "event" ? "event" : "snapshot",
        entity_id: (n.data as any).entityId,
        x: n.position.x,
        y: n.position.y,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        kind: ((e.data as any)?.kind || "note_to_event") as CanvasEdge["kind"],
        source_handle: e.sourceHandle ?? null,
        target_handle: e.targetHandle ?? null,
      })),
      viewport: rf.getViewport(),
    };
    api.canvas.save(novelId, nodeId, data).then(() => {
      setSaveState("saved");
      setTimeout(() => setSaveState("idle"), 1200);
    });
  }, [novelId, nodeId, nodes, edges, rf]);

  const scheduleSave = useCallback(() => {
    if (!loaded.current) return;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(persist, 700);
  }, [persist]);

  useEffect(() => {
    scheduleSave();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges]);

  const onConnect = useCallback(
    (conn: Connection) => {
      const src = nodes.find((n) => n.id === conn.source);
      const tgt = nodes.find((n) => n.id === conn.target);
      if (!src || !tgt || src.id === tgt.id) return;
      const kind = connectionKind(
        src.type === "event" ? "event" : "sticky",
        tgt.type === "event" ? "event" : "sticky",
      );
      if (!kind) {
        alert("只允许：便签→事件、事件→事件、事件→便签（变化）");
        return;
      }
      const edge: Edge = {
        id: genId("edge"),
        source: conn.source!,
        target: conn.target!,
        sourceHandle: conn.sourceHandle ?? undefined,
        targetHandle: conn.targetHandle ?? undefined,
        data: { kind },
        style: edgeStyleFor(kind),
      };
      setEdges((eds) => addEdge(edge, eds));
    },
    [nodes, setEdges],
  );

  const placeSnapshot = (snap: Snapshot) => {
    const center = rf.screenToFlowPosition({ x: window.innerWidth / 2, y: 250 });
    const node: Node = {
      id: genId("pl"),
      type: "sticky",
      position: nextNodePosition(center, placeSeq.current++),
      data: {
        entityId: snap.id,
        sourceType: snap.source_type,
        name: snap.name,
        label: snap.label,
        category: snap.category,
        summary: snapshotSummary(snap),
        highlight: false,
      },
    };
    setNodes((nds) => [...nds, node]);
  };

  const placeEvent = (ev: NovelEvent) => {
    const center = rf.screenToFlowPosition({ x: window.innerWidth / 2, y: 250 });
    const node: Node = {
      id: genId("pl"),
      type: "event",
      position: nextNodePosition(center, placeSeq.current++),
      data: {
        entityId: ev.id,
        title: ev.title,
        description: ev.description,
        timeLabel: ev.time_label || "",
        highlight: false,
      },
    };
    setNodes((nds) => [...nds, node]);
  };

  const createSnapshotFromCharacter = async (c: Character) => {
    if (!novelId) return;
    const snap: Snapshot = {
      id: genId("snap"),
      source_type: "character",
      source_id: c.id,
      name: c.name,
      label: "",
      category: "",
      fields: {
        role: c.role,
        appearance: c.appearance,
        personality: c.personality,
        background: c.background,
        abilities: c.abilities,
        speech_style: c.speech_style,
        arc: c.arc,
        current_state: c.current_state,
        relationships: c.relationships,
      },
    };
    await api.snapshots.add(novelId, snap);
    setSnapshots((s) => [...s, snap]);
    placeSnapshot(snap);
    setPicker(null);
  };

  const createSnapshotFromSetting = async (w: WorldSetting) => {
    if (!novelId) return;
    const snap: Snapshot = {
      id: genId("snap"),
      source_type: "setting",
      source_id: w.id,
      name: w.name,
      label: "",
      category: "",
      fields: {
        category: w.category,
        description: w.description,
        notable_features: w.notable_features,
      },
    };
    await api.snapshots.add(novelId, snap);
    setSnapshots((s) => [...s, snap]);
    placeSnapshot(snap);
    setPicker(null);
  };

  const onSelectNode = useCallback(
    (_: unknown, node: Node) => {
      setSelected(node);
      if (node.type === "sticky" && novelId) {
        api.snapshots.placements(novelId, (node.data as any).entityId).then(setPlacements);
      } else {
        setPlacements([]);
      }
    },
    [novelId],
  );

  if (!novelId || !nodeId) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 48px)" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 0",
          flexWrap: "wrap",
        }}
      >
        <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/novel/${novelId}/outline`)}>
          ← 大纲
        </button>
        <h2 style={{ margin: 0, fontSize: 16 }}>画板：{nodeId}</h2>
        <button className="btn btn-success btn-sm" onClick={() => setPicker("note")}>
          + 便签
        </button>
        <button className="btn btn-primary btn-sm" onClick={() => setPicker("event")}>
          + 事件
        </button>
        <span style={{ fontSize: 12, color: "#22c55e", marginLeft: 8 }}>
          {saveState === "saving" ? "保存中..." : saveState === "saved" ? "已保存" : ""}
        </span>
      </div>

      <div style={{ flex: 1, display: "flex", border: "1px solid var(--border, #ddd)", borderRadius: 8, overflow: "hidden" }}>
        <div style={{ flex: 1, position: "relative" }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            connectionMode={ConnectionMode.Loose}
            deleteKeyCode={["Backspace", "Delete"]}
            onNodeClick={(_, n) => { setSelectedEdge(null); onSelectNode(_, n); }}
            onEdgeClick={(_, e) => { setSelected(null); setPlacements([]); setSelectedEdge(e); }}
            onPaneClick={() => { setSelected(null); setPlacements([]); setSelectedEdge(null); }}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.1}
            maxZoom={4}
          >
            <Background gap={16} />
            <Controls />
            <MiniMap pannable zoomable />
          </ReactFlow>
        </div>

        {selected && (
          <div style={{ width: 260, borderLeft: "1px solid #ddd", padding: 12, overflow: "auto", fontSize: 13 }}>
            <Inspector
              novelId={novelId}
              node={selected}
              placements={placements}
              currentNodeId={nodeId}
              onJump={(p) => navigate(`/novel/${novelId}/canvas/${p.node_id}?focus=${p.placement_id}`)}
              onDeletePlacement={() => {
                setNodes((nds) => nds.filter((n) => n.id !== selected.id));
                setEdges((eds) => eds.filter((e) => e.source !== selected.id && e.target !== selected.id));
                setSelected(null);
              }}
              onSnapshotSaved={(snap) => {
                setSnapshots((arr) => arr.map((s) => (s.id === snap.id ? snap : s)));
                setNodes((nds) =>
                  nds.map((n) =>
                    n.id === selected.id
                      ? { ...n, data: { ...n.data, name: snap.name, label: snap.label, category: snap.category, summary: snapshotSummary(snap) } }
                      : n,
                  ),
                );
              }}
              snapshots={snapshots}
              events={events}
            />
          </div>
        )}

        {selectedEdge && (
          <div style={{ width: 260, borderLeft: "1px solid #ddd", padding: 12, overflow: "auto", fontSize: 13 }}>
            <h4 style={{ marginTop: 0 }}>连线</h4>
            <p style={{ fontSize: 12, color: "#666" }}>
              类型：{edgeKindLabel(((selectedEdge.data as any)?.kind) || "note_to_event")}
            </p>
            <button
              className="btn btn-danger btn-sm"
              onClick={() => {
                setEdges((eds) => eds.filter((e) => e.id !== selectedEdge.id));
                setSelectedEdge(null);
              }}
            >
              删除连线
            </button>
            <p style={{ fontSize: 11, color: "#999", marginTop: 8 }}>提示：选中连线后也可按 Delete / Backspace 删除。</p>
          </div>
        )}
      </div>

      {picker === "note" && (
        <Modal title="添加便签" onClose={() => setPicker(null)}>
          <NotePicker
            novelId={novelId}
            characters={characters}
            world={world}
            snapshots={snapshots}
            onPickExisting={(s) => { placeSnapshot(s); setPicker(null); }}
            onFromCharacter={createSnapshotFromCharacter}
            onFromSetting={createSnapshotFromSetting}
            onCreated={(s) => { setSnapshots((arr) => [...arr, s]); placeSnapshot(s); setPicker(null); }}
          />
        </Modal>
      )}
      {picker === "event" && (
        <Modal title="添加事件" onClose={() => setPicker(null)}>
          <EventPicker
            novelId={novelId}
            events={events}
            onPickExisting={(e) => { placeEvent(e); setPicker(null); }}
            onCreated={(e) => { setEvents((arr) => [...arr, e]); placeEvent(e); setPicker(null); }}
          />
        </Modal>
      )}
    </div>
  );
}

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}
      onClick={onClose}
    >
      <div className="card" style={{ width: 460, maxHeight: "80vh", overflow: "auto" }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function NotePicker({
  novelId,
  characters,
  world,
  snapshots,
  onPickExisting,
  onFromCharacter,
  onFromSetting,
  onCreated,
}: {
  novelId: string;
  characters: Character[];
  world: WorldSetting[];
  snapshots: Snapshot[];
  onPickExisting: (s: Snapshot) => void;
  onFromCharacter: (c: Character) => void;
  onFromSetting: (w: WorldSetting) => void;
  onCreated: (s: Snapshot) => void;
}) {
  const [name, setName] = useState("");
  const [summary, setSummary] = useState("");
  const [type, setType] = useState<"free" | "character" | "setting">("free");
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  const createNew = async () => {
    if (!name.trim()) return;
    const snap: Snapshot = {
      id: genId("snap"),
      source_type: type,
      source_id: null,
      name,
      label: "",
      category: category.trim(),
      fields: type === "setting" ? { description: summary } : { personality: summary },
    };
    await api.snapshots.add(novelId, { ...snap, create_master: type !== "free" });
    onCreated(snap);
  };

  const q = search.trim().toLowerCase();
  const matchText = (...vals: (string | null | undefined)[]) =>
    !q || vals.some((v) => (v || "").toLowerCase().includes(q));

  const customCats = Array.from(
    new Set(snapshots.map((s) => (s.category || "").trim()).filter(Boolean)),
  );

  const showChars = filter === "all" || filter === "character";
  const showSettings = filter === "all" || filter === "setting";

  const filteredChars = characters.filter((c) => matchText(c.name));
  const filteredWorld = world.filter((w) => matchText(w.name));
  const filteredSnaps = snapshots.filter((s) => {
    if (!matchText(s.name, s.label, s.category)) return false;
    if (filter === "all") return true;
    if (filter === "character" || filter === "setting" || filter === "free") {
      return s.source_type === filter;
    }
    return (s.category || "").trim() === filter;
  });

  const chips: { value: string; label: string }[] = [
    { value: "all", label: "全部" },
    { value: "character", label: "角色" },
    { value: "setting", label: "设定" },
    { value: "free", label: "自由" },
    ...customCats.map((c) => ({ value: c, label: `#${c}` })),
  ];

  return (
    <div>
      <div className="form-group">
        <input
          type="text"
          placeholder="🔍 搜索名称 / 标注 / 分类..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
        {chips.map((ch) => (
          <button
            key={ch.value}
            className="btn btn-sm"
            style={{
              background: filter === ch.value ? "#3b82f6" : "var(--btn-bg, #e5e7eb)",
              color: filter === ch.value ? "#fff" : "#374151",
            }}
            onClick={() => setFilter(ch.value)}
          >
            {ch.label}
          </button>
        ))}
      </div>

      {showChars && (
        <div className="form-group">
          <label>从角色生成快照</label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {filteredChars.map((c) => (
              <button key={c.id} className="btn btn-secondary btn-sm" onClick={() => onFromCharacter(c)}>{c.name}</button>
            ))}
            {filteredChars.length === 0 && <span style={{ color: "#999", fontSize: 12 }}>无匹配角色</span>}
          </div>
        </div>
      )}
      {showSettings && (
        <div className="form-group">
          <label>从设定生成快照</label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {filteredWorld.map((w) => (
              <button key={w.id} className="btn btn-secondary btn-sm" onClick={() => onFromSetting(w)}>{w.name}</button>
            ))}
            {filteredWorld.length === 0 && <span style={{ color: "#999", fontSize: 12 }}>无匹配设定</span>}
          </div>
        </div>
      )}
      <div className="form-group">
        <label>复用已有快照</label>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {filteredSnaps.map((s) => (
            <button key={s.id} className="btn btn-sm" style={{ background: NOTE_COLORS[s.source_type], color: "#1f2937" }} onClick={() => onPickExisting(s)}>
              {s.name}{s.category ? ` #${s.category}` : ""}
            </button>
          ))}
          {filteredSnaps.length === 0 && <span style={{ color: "#999", fontSize: 12 }}>无匹配快照</span>}
        </div>
      </div>
      <hr style={{ margin: "12px 0", opacity: 0.2 }} />
      <div className="form-group">
        <label>新建便签</label>
        <input type="text" placeholder="名称" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="form-group">
        <label>类型</label>
        <select value={type} onChange={(e) => setType(e.target.value as any)}>
          <option value="free">自由便签</option>
          <option value="character">创建为新角色（同步主卡）</option>
          <option value="setting">创建为新设定（同步主卡）</option>
        </select>
      </div>
      <div className="form-group">
        <label>分类（可选标签，便于检索）</label>
        <input
          type="text"
          placeholder="如：主角阵营 / 反派 / 地点..."
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          list="snapshot-category-options"
        />
        <datalist id="snapshot-category-options">
          {customCats.map((c) => (
            <option key={c} value={c} />
          ))}
        </datalist>
      </div>
      <div className="form-group">
        <textarea placeholder="描述/性格..." value={summary} onChange={(e) => setSummary(e.target.value)} rows={2} />
      </div>
      <button className="btn btn-success" onClick={createNew}>创建并放置</button>
    </div>
  );
}

function EventPicker({
  novelId,
  events,
  onPickExisting,
  onCreated,
}: {
  novelId: string;
  events: NovelEvent[];
  onPickExisting: (e: NovelEvent) => void;
  onCreated: (e: NovelEvent) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [timeLabel, setTimeLabel] = useState("");

  const createNew = async () => {
    if (!title.trim()) return;
    const ev: NovelEvent = { id: genId("ev"), title, description, time_label: timeLabel || null };
    await api.events.add(novelId, ev);
    onCreated(ev);
  };

  return (
    <div>
      <div className="form-group">
        <label>复用已有事件</label>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {events.map((e) => (
            <button key={e.id} className="btn btn-secondary btn-sm" onClick={() => onPickExisting(e)}>⚡ {e.title}</button>
          ))}
          {events.length === 0 && <span style={{ color: "#999", fontSize: 12 }}>暂无事件</span>}
        </div>
      </div>
      <hr style={{ margin: "12px 0", opacity: 0.2 }} />
      <div className="form-group">
        <label>新建事件</label>
        <input type="text" placeholder="标题" value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>
      <div className="form-group">
        <input type="text" placeholder="时间标签（可选）" value={timeLabel} onChange={(e) => setTimeLabel(e.target.value)} />
      </div>
      <div className="form-group">
        <textarea placeholder="事件描述..." value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
      </div>
      <button className="btn btn-success" onClick={createNew}>创建并放置</button>
    </div>
  );
}

function Inspector({
  novelId,
  node,
  placements,
  currentNodeId,
  onJump,
  onDeletePlacement,
  onSnapshotSaved,
  snapshots,
}: {
  novelId: string;
  node: Node;
  placements: SnapshotPlacement[];
  currentNodeId: string;
  onJump: (p: SnapshotPlacement) => void;
  onDeletePlacement: () => void;
  onSnapshotSaved: (s: Snapshot) => void;
  snapshots: Snapshot[];
  events: NovelEvent[];
}) {
  const isSticky = node.type === "sticky";
  const snap = snapshots.find((s) => s.id === (node.data as any).entityId);
  const [label, setLabel] = useState((node.data as any).label || "");
  const [category, setCategory] = useState((node.data as any).category || "");
  const [summary, setSummary] = useState((node.data as any).summary || "");

  useEffect(() => {
    setLabel((node.data as any).label || "");
    setCategory((node.data as any).category || "");
    setSummary((node.data as any).summary || "");
  }, [node.id]);

  const saveSnap = async () => {
    if (!snap) return;
    const field = snap.source_type === "setting" ? "description" : "personality";
    const updated: Snapshot = { ...snap, label, category: category.trim(), fields: { ...snap.fields, [field]: summary } };
    await api.snapshots.update(novelId, snap.id, updated);
    onSnapshotSaved(updated);
  };

  return (
    <div>
      <h4 style={{ marginTop: 0 }}>{isSticky ? "便签" : "事件"}：{(node.data as any).name || (node.data as any).title}</h4>
      {isSticky && snap && (
        <>
          <div className="form-group">
            <label>历史标注（如"重伤后"）</label>
            <input type="text" value={label} onChange={(e) => setLabel(e.target.value)} />
          </div>
          <div className="form-group">
            <label>分类</label>
            <input type="text" placeholder="分类标签" value={category} onChange={(e) => setCategory(e.target.value)} />
          </div>
          <div className="form-group">
            <label>内容</label>
            <textarea value={summary} onChange={(e) => setSummary(e.target.value)} rows={4} />
          </div>
          <button className="btn btn-primary btn-sm" onClick={saveSnap}>保存快照</button>
          <p style={{ fontSize: 11, color: "#999", marginTop: 4 }}>编辑历史快照不会修改主角色/设定卡。</p>

          <h5 style={{ marginTop: 16, marginBottom: 6 }}>定位 · 在其他画板中使用</h5>
          {placements.filter((p) => p.node_id !== currentNodeId).length === 0 && (
            <p style={{ fontSize: 12, color: "#999" }}>暂未在其他画板使用</p>
          )}
          {placements
            .filter((p) => p.node_id !== currentNodeId)
            .map((p) => (
              <div key={p.placement_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <span style={{ fontSize: 12 }}>{p.node_title || p.node_id}</span>
                <button className="btn btn-secondary btn-sm" onClick={() => onJump(p)}>定位</button>
              </div>
            ))}
        </>
      )}
      <hr style={{ margin: "12px 0", opacity: 0.2 }} />
      <button className="btn btn-danger btn-sm" onClick={onDeletePlacement}>从画板移除</button>
    </div>
  );
}

export default function CanvasPage() {
  return (
    <ReactFlowProvider>
      <CanvasInner />
    </ReactFlowProvider>
  );
}
