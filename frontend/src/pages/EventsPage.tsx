import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, NovelEvent } from "../api/client";

function genId() {
  return "ev-" + Math.random().toString(36).slice(2, 10);
}

export default function EventsPage() {
  const { novelId } = useParams<{ novelId: string }>();
  const [events, setEvents] = useState<NovelEvent[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<NovelEvent>>({});

  useEffect(() => {
    if (novelId) api.events.list(novelId).then(setEvents);
  }, [novelId]);

  if (!novelId) return null;

  const startNew = () => {
    const id = genId();
    setForm({ id, title: "", description: "", time_label: "" });
    setEditingId(id);
  };

  const startEdit = (e: NovelEvent) => {
    setForm({ ...e });
    setEditingId(e.id);
  };

  const save = async () => {
    if (!form.title) return;
    const ev: NovelEvent = {
      id: form.id || genId(),
      title: form.title || "",
      description: form.description || "",
      time_label: form.time_label || null,
    };
    const exists = events.find((e) => e.id === ev.id);
    if (exists) {
      await api.events.update(novelId, ev.id, ev);
      setEvents(events.map((e) => (e.id === ev.id ? ev : e)));
    } else {
      await api.events.add(novelId, ev);
      setEvents([...events, ev]);
    }
    setEditingId(null);
    setForm({});
  };

  const remove = async (id: string) => {
    await api.events.delete(novelId, id);
    setEvents(events.filter((e) => e.id !== id));
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <h2>事件（全局）</h2>
        <button className="btn btn-success" onClick={startNew}>+ 新事件</button>
      </div>

      {editingId && (
        <div className="card">
          <h3 style={{ fontSize: 14, marginBottom: 12 }}>
            {events.find((e) => e.id === editingId) ? "编辑事件" : "新建事件"}
          </h3>
          <div className="form-group">
            <label>标题</label>
            <input type="text" value={form.title || ""} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="form-group">
            <label>时间标签</label>
            <input type="text" value={form.time_label || ""} onChange={(e) => setForm({ ...form, time_label: e.target.value })} />
          </div>
          <div className="form-group">
            <label>描述</label>
            <textarea value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" onClick={save}>保存</button>
            <button className="btn btn-secondary" onClick={() => setEditingId(null)}>取消</button>
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {events.map((e) => (
          <div key={e.id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>⚡ {e.title}</strong>
              {e.time_label && <span className="tag">{e.time_label}</span>}
            </div>
            {e.description && <p style={{ fontSize: 13, color: "#555", marginTop: 4 }}>{e.description}</p>}
            <div style={{ marginTop: 8, display: "flex", gap: 4 }}>
              <button className="btn btn-secondary btn-sm" onClick={() => startEdit(e)}>编辑</button>
              <button className="btn btn-danger btn-sm" onClick={() => remove(e.id)}>删除</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
