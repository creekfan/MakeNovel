import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { api, WorldSetting } from "../api/client";

function generateId() {
  return "ws-" + Math.random().toString(36).slice(2, 10);
}

const CATEGORIES = ["location", "faction", "rule", "race", "item", "profession", "history"];
const CATEGORY_LABELS: Record<string, string> = {
  location: "环境场景",
  faction: "势力组织",
  rule: "世界观规则",
  race: "种族物种",
  item: "重要物品",
  profession: "职业",
  history: "历史事件",
};

function EditForm({
  form,
  setForm,
  onSave,
  onCancel,
}: {
  form: Partial<WorldSetting>;
  setForm: (f: Partial<WorldSetting>) => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  const [featureInput, setFeatureInput] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, []);

  const addFeature = () => {
    if (!featureInput.trim()) return;
    setForm({ ...form, notable_features: [...(form.notable_features || []), featureInput.trim()] });
    setFeatureInput("");
  };

  const removeFeature = (idx: number) => {
    setForm({ ...form, notable_features: (form.notable_features || []).filter((_, i) => i !== idx) });
  };

  return (
    <div ref={ref} className="card" style={{ border: "2px solid #4a6cf7" }}>
      <div className="form-group">
        <label>名称</label>
        <input type="text" value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </div>
      <div className="form-group">
        <label>类别</label>
        <select value={form.category || "rule"} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
          ))}
        </select>
      </div>
      <div className="form-group">
        <label>描述</label>
        <textarea value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </div>
      <div className="form-group">
        <label>显著特征</label>
        <div style={{ display: "flex", gap: 4, marginBottom: 4 }}>
          <input
            type="text"
            value={featureInput}
            onChange={(e) => setFeatureInput(e.target.value)}
            placeholder="输入特征后回车"
            onKeyDown={(e) => e.key === "Enter" && addFeature()}
            style={{ marginBottom: 0 }}
          />
          <button className="btn btn-secondary btn-sm" onClick={addFeature}>添加</button>
        </div>
        <div>
          {(form.notable_features || []).map((f, i) => (
            <span key={i} className="tag" style={{ cursor: "pointer" }} onClick={() => removeFeature(i)}>
              {f} ×
            </span>
          ))}
        </div>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button className="btn btn-primary" onClick={onSave}>保存</button>
        <button className="btn btn-secondary" onClick={onCancel}>取消</button>
      </div>
    </div>
  );
}

export default function WorldPage() {
  const { novelId } = useParams<{ novelId: string }>();
  const [settings, setSettings] = useState<WorldSetting[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<WorldSetting>>({});
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  useEffect(() => {
    if (novelId) api.world.get(novelId).then(setSettings);
  }, [novelId]);

  if (!novelId) return null;

  const startNew = (category?: string) => {
    const id = generateId();
    setForm({ id, name: "", category: category || activeCategory || "rule", description: "", notable_features: [] });
    setEditingId(id);
  };

  const startEdit = (w: WorldSetting) => {
    setForm({ ...w });
    setEditingId(w.id);
  };

  const saveSetting = async () => {
    if (!form.name) return;
    const item: WorldSetting = {
      id: form.id || generateId(),
      name: form.name || "",
      category: form.category || "rule",
      description: form.description || "",
      notable_features: form.notable_features || [],
    };
    const exists = settings.find((s) => s.id === item.id);
    const updated = exists
      ? settings.map((s) => (s.id === item.id ? item : s))
      : [...settings, item];
    setSettings(updated);
    await api.world.save(novelId, updated);
    setEditingId(null);
    setForm({});
  };

  const deleteSetting = async (id: string) => {
    const updated = settings.filter((s) => s.id !== id);
    setSettings(updated);
    await api.world.save(novelId, updated);
    if (editingId === id) {
      setEditingId(null);
      setForm({});
    }
  };

  const categoryCounts: Record<string, number> = {};
  for (const s of settings) {
    categoryCounts[s.category] = (categoryCounts[s.category] || 0) + 1;
  }

  const filtered = activeCategory
    ? settings.filter((s) => s.category === activeCategory)
    : settings;

  const isNewItem = editingId !== null && !settings.find((s) => s.id === editingId);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2>世界观设定</h2>
        <button className="btn btn-success" onClick={() => startNew()}>
          + 新设定
        </button>
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16 }}>
        <button
          className="btn btn-sm"
          style={{
            background: activeCategory === null ? "#4a6cf7" : "#e5e7eb",
            color: activeCategory === null ? "#fff" : "#333",
          }}
          onClick={() => setActiveCategory(null)}
        >
          全部 ({settings.length})
        </button>
        {CATEGORIES.map((cat) => {
          const count = categoryCounts[cat] || 0;
          if (count === 0 && activeCategory !== cat) return null;
          return (
            <button
              key={cat}
              className="btn btn-sm"
              style={{
                background: activeCategory === cat ? "#4a6cf7" : "#e5e7eb",
                color: activeCategory === cat ? "#fff" : "#333",
              }}
              onClick={() => setActiveCategory(activeCategory === cat ? null : cat)}
            >
              {CATEGORY_LABELS[cat]} ({count})
            </button>
          );
        })}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {filtered.map((w) =>
          editingId === w.id ? (
            <EditForm
              key={w.id}
              form={form}
              setForm={setForm}
              onSave={saveSetting}
              onCancel={() => { setEditingId(null); setForm({}); }}
            />
          ) : (
            <div key={w.id} className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>{w.name}</strong>
                <span className="tag">{CATEGORY_LABELS[w.category] || w.category}</span>
              </div>
              {w.description && (
                <p style={{ fontSize: 13, color: "#555", marginTop: 4, whiteSpace: "pre-line" }}>
                  {w.description.length > 120 ? w.description.slice(0, 120) + "..." : w.description}
                </p>
              )}
              {w.notable_features.length > 0 && (
                <div style={{ marginTop: 4 }}>
                  {w.notable_features.map((f, i) => (
                    <span key={i} className="tag">{f}</span>
                  ))}
                </div>
              )}
              <div style={{ marginTop: 8, display: "flex", gap: 4 }}>
                <button className="btn btn-secondary btn-sm" onClick={() => startEdit(w)}>编辑</button>
                <button className="btn btn-danger btn-sm" onClick={() => deleteSetting(w.id)}>删除</button>
              </div>
            </div>
          )
        )}
        {isNewItem && (
          <EditForm
            form={form}
            setForm={setForm}
            onSave={saveSetting}
            onCancel={() => { setEditingId(null); setForm({}); }}
          />
        )}
      </div>
    </div>
  );
}
