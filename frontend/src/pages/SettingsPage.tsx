import { useState } from "react";
import { useSettingsStore } from "../store/settings";

export default function SettingsPage() {
  const { settings, save, clear } = useSettingsStore();
  const [form, setForm] = useState({ ...settings });
  const [showKey, setShowKey] = useState(false);

  const handleSave = () => {
    save(form);
    alert("设置已保存（安全缓存在浏览器本地）");
  };

  return (
    <div style={{ maxWidth: 500 }}>
      <h2 style={{ marginBottom: 16 }}>模型设置</h2>
      <div className="card">
        <p style={{ fontSize: 12, color: "#6b7280", marginBottom: 16 }}>
          API Key 使用 Base64 编码存储在浏览器 localStorage 中，不会发送到本服务器，仅在调用 Agent 时直接传递给 LLM API。
        </p>
        <div className="form-group">
          <label>API Key</label>
          <div style={{ display: "flex", gap: 4 }}>
            <input
              type={showKey ? "text" : "password"}
              value={form.apiKey}
              onChange={(e) => setForm({ ...form, apiKey: e.target.value })}
              placeholder="sk-..."
              style={{ marginBottom: 0 }}
            />
            <button className="btn btn-secondary btn-sm" onClick={() => setShowKey(!showKey)}>
              {showKey ? "隐藏" : "显示"}
            </button>
          </div>
        </div>
        <div className="form-group">
          <label>模型</label>
          <input
            type="text"
            value={form.model}
            onChange={(e) => setForm({ ...form, model: e.target.value })}
            placeholder="deepseek-chat"
          />
        </div>
        <div className="form-group">
          <label>API Base URL</label>
          <input
            type="text"
            value={form.baseUrl}
            onChange={(e) => setForm({ ...form, baseUrl: e.target.value })}
            placeholder="https://api.deepseek.com"
          />
        </div>
        <div className="settings-grid">
          <div className="form-group">
            <label>Temperature</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={form.temperature}
              onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })}
            />
          </div>
          <div className="form-group">
            <label>Max Tokens</label>
            <input
              type="number"
              step="512"
              min="256"
              max="32768"
              value={form.maxTokens}
              onChange={(e) => setForm({ ...form, maxTokens: parseInt(e.target.value) })}
            />
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <button className="btn btn-primary" onClick={handleSave}>保存设置</button>
          <button className="btn btn-danger" onClick={() => { clear(); setForm({ apiKey: "", model: "deepseek-chat", baseUrl: "https://api.deepseek.com", temperature: 0.7, maxTokens: 10000 }); }}>
            清除设置
          </button>
        </div>
      </div>
    </div>
  );
}
