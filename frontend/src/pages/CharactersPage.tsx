import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, Character } from "../api/client";

function generateId() {
  return "char-" + Math.random().toString(36).slice(2, 10);
}

const ROLES = ["protagonist", "antagonist", "supporting", "minor"];

export default function CharactersPage() {
  const { novelId } = useParams<{ novelId: string }>();
  const [characters, setCharacters] = useState<Character[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<Character>>({});

  useEffect(() => {
    if (novelId) api.characters.get(novelId).then(setCharacters);
  }, [novelId]);

  if (!novelId) return null;

  const startNew = () => {
    const id = generateId();
    setForm({ id, name: "", role: "supporting", appearance: "", personality: "", background: "", relationships: [] });
    setEditingId(id);
  };

  const startEdit = (c: Character) => {
    setForm({ ...c });
    setEditingId(c.id);
  };

  const saveChar = async () => {
    if (!form.name) return;
    const char: Character = {
      id: form.id || generateId(),
      name: form.name || "",
      role: form.role || "supporting",
      appearance: form.appearance || "",
      personality: form.personality || "",
      background: form.background || "",
      abilities: form.abilities || null,
      speech_style: form.speech_style || null,
      arc: form.arc || null,
      current_state: form.current_state || null,
      relationships: form.relationships || [],
    };
    const exists = characters.find((c) => c.id === char.id);
    const updated = exists
      ? characters.map((c) => (c.id === char.id ? char : c))
      : [...characters, char];
    setCharacters(updated);
    await api.characters.save(novelId, updated);
    setEditingId(null);
    setForm({});
  };

  const deleteChar = async (id: string) => {
    const updated = characters.filter((c) => c.id !== id);
    setCharacters(updated);
    await api.characters.save(novelId, updated);
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <h2>角色卡片</h2>
        <button className="btn btn-success" onClick={startNew}>
          + 新角色
        </button>
      </div>

      {editingId && (
        <div className="card">
          <h3 style={{ fontSize: 14, marginBottom: 12 }}>
            {characters.find((c) => c.id === editingId) ? "编辑角色" : "新建角色"}
          </h3>
          <div className="form-group">
            <label>名称</label>
            <input type="text" value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="form-group">
            <label>定位</label>
            <select value={form.role || "supporting"} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              {ROLES.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>外貌</label>
            <textarea value={form.appearance || ""} onChange={(e) => setForm({ ...form, appearance: e.target.value })} />
          </div>
          <div className="form-group">
            <label>性格</label>
            <textarea value={form.personality || ""} onChange={(e) => setForm({ ...form, personality: e.target.value })} />
          </div>
          <div className="form-group">
            <label>背景</label>
            <textarea value={form.background || ""} onChange={(e) => setForm({ ...form, background: e.target.value })} />
          </div>
          <div className="form-group">
            <label>能力/特长</label>
            <input type="text" value={form.abilities || ""} onChange={(e) => setForm({ ...form, abilities: e.target.value })} />
          </div>
          <div className="form-group">
            <label>说话风格</label>
            <input type="text" value={form.speech_style || ""} onChange={(e) => setForm({ ...form, speech_style: e.target.value })} />
          </div>
          <div className="form-group">
            <label>角色弧光</label>
            <input type="text" value={form.arc || ""} onChange={(e) => setForm({ ...form, arc: e.target.value })} />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" onClick={saveChar}>保存</button>
            <button className="btn btn-secondary" onClick={() => setEditingId(null)}>取消</button>
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {characters.map((c) => (
          <div key={c.id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>{c.name}</strong>
              <span className="tag">{c.role}</span>
            </div>
            {c.personality && <p style={{ fontSize: 13, color: "#555", marginTop: 4 }}>{c.personality}</p>}
            <div style={{ marginTop: 8, display: "flex", gap: 4 }}>
              <button className="btn btn-secondary btn-sm" onClick={() => startEdit(c)}>编辑</button>
              <button className="btn btn-danger btn-sm" onClick={() => deleteChar(c.id)}>删除</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
