import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api, Novel } from "../api/client";
import { useThemeStore } from "../store/theme";

export default function HomePage() {
  const [novels, setNovels] = useState<Novel[]>([]);
  const [name, setName] = useState("");
  const navigate = useNavigate();
  const { dark, toggle } = useThemeStore();

  useEffect(() => {
    api.novels.list().then(setNovels);
  }, []);

  const handleCreate = async () => {
    if (!name.trim()) return;
    const novel = await api.novels.create(name.trim());
    setName("");
    navigate(`/novel/${novel.id}`);
  };

  const handleDelete = async (id: string) => {
    await api.novels.delete(id);
    setNovels(novels.filter((n) => n.id !== id));
  };

  return (
    <div style={{ maxWidth: 600, margin: "80px auto", padding: "0 20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1>NovelAgent - AI 小说写作工具</h1>
        <button className="btn btn-secondary btn-sm" onClick={toggle}>
          {dark ? "☀ 浅色" : "☾ 深色"}
        </button>
      </div>
      <div className="card">
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>新建项目</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            placeholder="输入小说名称..."
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            style={{ marginBottom: 0 }}
          />
          <button className="btn btn-primary" onClick={handleCreate}>
            创建
          </button>
        </div>
      </div>
      <div className="card">
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>我的项目</h2>
        {novels.length === 0 && <p style={{ color: "#999" }}>暂无项目</p>}
        {novels.map((n) => (
          <div
            key={n.id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "10px 0",
              borderBottom: "1px solid #eee",
            }}
          >
            <span
              style={{ cursor: "pointer", fontWeight: 500 }}
              onClick={() => navigate(`/novel/${n.id}`)}
            >
              {n.name}
            </span>
            <button className="btn btn-danger btn-sm" onClick={() => handleDelete(n.id)}>
              删除
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
