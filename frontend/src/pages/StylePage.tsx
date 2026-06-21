import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";

interface StyleItem {
  id: string;
  name: string;
  created_at: string;
}

interface StyleDetail extends StyleItem {
  content: string;
}

export default function StylePage() {
  const { novelId } = useParams<{ novelId: string }>();
  const [styles, setStyles] = useState<StyleItem[]>([]);
  const [editing, setEditing] = useState<StyleDetail | null>(null);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [content, setContent] = useState("");

  const load = () => {
    if (novelId) api.styles.list(novelId).then(setStyles);
  };

  useEffect(() => { load(); }, [novelId]);

  const startCreate = () => {
    setCreating(true);
    setEditing(null);
    setName("");
    setContent("");
  };

  const startEdit = async (styleId: string) => {
    if (!novelId) return;
    const s = await api.styles.get(novelId, styleId);
    setEditing(s);
    setCreating(false);
    setName(s.name);
    setContent(s.content);
  };

  const save = async () => {
    if (!novelId || !name.trim() || !content.trim()) return;
    if (creating) {
      await api.styles.create(novelId, name.trim(), content);
    } else if (editing) {
      await api.styles.update(novelId, editing.id, name.trim(), content);
    }
    setCreating(false);
    setEditing(null);
    load();
  };

  const remove = async (styleId: string) => {
    if (!novelId) return;
    if (!confirm("确定删除这个文风？")) return;
    await api.styles.delete(novelId, styleId);
    if (editing?.id === styleId) {
      setEditing(null);
      setCreating(false);
    }
    load();
  };

  return (
    <div className="style-page">
      <div className="style-list-panel">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <h2 style={{ fontSize: 16 }}>文风列表</h2>
          <button className="btn btn-primary btn-sm" onClick={startCreate}>+ 新建</button>
        </div>
        {styles.length === 0 && (
          <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>暂无文风，点击「新建」创建第一个</p>
        )}
        {styles.map((s) => (
          <div
            key={s.id}
            onClick={() => startEdit(s.id)}
            style={{
              padding: "8px 10px",
              marginBottom: 4,
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 13,
              background: editing?.id === s.id ? "var(--bg-hover)" : "transparent",
            }}
            onMouseEnter={(e) => {
              if (editing?.id !== s.id) (e.target as HTMLElement).style.background = "var(--bg-hover)";
            }}
            onMouseLeave={(e) => {
              if (editing?.id !== s.id) (e.target as HTMLElement).style.background = "transparent";
            }}
          >
            <div style={{ fontWeight: 500 }}>{s.name}</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
              {s.created_at ? new Date(s.created_at).toLocaleString() : ""}
            </div>
          </div>
        ))}
      </div>

      <div className="style-editor-panel">
        {(creating || editing) ? (
          <>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                名称
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：龙族文风"
                style={{ width: "100%", fontSize: 13 }}
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                文风 Prompt（粘贴你的写作指导） 
              </label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={20}
                style={{ width: "100%", fontSize: 13, resize: "vertical", fontFamily: "monospace" }}
                placeholder="粘贴文风指导 prompt..."
              />
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-primary btn-sm" onClick={save}>
                {creating ? "创建" : "保存"}
              </button>
              <button className="btn btn-sm" onClick={() => { setCreating(false); setEditing(null); }}
                style={{ background: "var(--bg-card)", color: "var(--text)", border: "1px solid var(--border-light)" }}>
                取消
              </button>
              {editing && (
                <button className="btn btn-sm" onClick={() => remove(editing.id)}
                  style={{ marginLeft: "auto", background: "transparent", color: "#ef4444", border: "1px solid #ef4444" }}>
                  删除
                </button>
              )}
            </div>
          </>
        ) : (
          <div style={{ textAlign: "center", color: "var(--text-muted)", marginTop: 80, fontSize: 13 }}>
            选择左侧文风查看或编辑，或点击「新建」
          </div>
        )}
      </div>
    </div>
  );
}
