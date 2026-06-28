import { NavLink, Outlet, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { api, Novel } from "../api/client";
import { useSettingsStore } from "../store/settings";
import { useThemeStore } from "../store/theme";
import OutlineAssistant from "./OutlineAssistant";

export default function NovelLayout() {
  const { novelId } = useParams<{ novelId: string }>();
  const [novel, setNovel] = useState<Novel | null>(null);
  const { dark, toggle } = useThemeStore();
  const settings = useSettingsStore((s) => s.settings);

  const [showAss, setShowAss] = useState(false);
  const [assMsgs, setAssMsgs] = useState<{ role: "user" | "assistant"; content: string }[]>([]);
  const [assLoading, setAssLoading] = useState(false);

  useEffect(() => {
    if (novelId) api.novels.get(novelId).then(setNovel);
  }, [novelId]);

  if (!novelId) return null;

  const onAssSend = async (text: string) => {
    const msgs = [...assMsgs, { role: "user" as const, content: text }];
    setAssMsgs(msgs);
    setAssLoading(true);
    try {
      const res = await api.outline.assistant(novelId, {
        messages: msgs,
        api_key: settings.apiKey,
        model: settings.model,
        base_url: settings.baseUrl,
        temperature: settings.temperature,
      });
      setAssMsgs([...msgs, { role: "assistant", content: res.reply }]);
    } catch (e: any) {
      setAssMsgs([...msgs, { role: "assistant", content: `错误：${e.message}` }]);
    } finally {
      setAssLoading(false);
    }
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <h1>{novel?.name || "..."}</h1>
        <nav>
          <NavLink to={`/novel/${novelId}/outline`}>大纲目录</NavLink>
          <NavLink to={`/novel/${novelId}/characters`}>角色卡片</NavLink>
          <NavLink to={`/novel/${novelId}/world`}>世界观设定</NavLink>
          <NavLink to={`/novel/${novelId}/events`}>事件</NavLink>
          <NavLink to={`/novel/${novelId}/styles`}>文风</NavLink>
          <NavLink to={`/novel/${novelId}/logs`}>运行日志</NavLink>
          <NavLink to={`/novel/${novelId}/settings`}>模型设置</NavLink>
          <button className="btn btn-sm" style={{ background: "#8b5cf6", color: "#fff", marginTop: 8, width: "100%" }}
            onClick={() => setShowAss(true)}>
            大纲助手
          </button>
          <NavLink to="/" style={{ marginTop: "auto", opacity: 0.6 }}>
            ← 返回首页
          </NavLink>
        </nav>
        <div className="theme-toggle" onClick={toggle}>
          <span>{dark ? "☀" : "☾"}</span>
          <span>{dark ? "浅色模式" : "深色模式"}</span>
        </div>
      </aside>
      <main className="main-content">
        <Outlet context={{ openAssistant: () => setShowAss(true) }} />
      </main>

      {showAss && (
        <OutlineAssistant
          messages={assMsgs}
          onSend={onAssSend}
          onClose={() => setShowAss(false)}
          onReset={() => setAssMsgs([])}
          loading={assLoading}
        />
      )}
    </div>
  );
}
