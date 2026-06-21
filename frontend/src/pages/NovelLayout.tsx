import { NavLink, Outlet, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { api, Novel } from "../api/client";
import { useThemeStore } from "../store/theme";

export default function NovelLayout() {
  const { novelId } = useParams<{ novelId: string }>();
  const [novel, setNovel] = useState<Novel | null>(null);
  const { dark, toggle } = useThemeStore();

  useEffect(() => {
    if (novelId) api.novels.get(novelId).then(setNovel);
  }, [novelId]);

  if (!novelId) return null;

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <h1>{novel?.name || "..."}</h1>
        <nav>
          <NavLink to={`/novel/${novelId}/outline`}>大纲目录</NavLink>
          <NavLink to={`/novel/${novelId}/characters`}>角色卡片</NavLink>
          <NavLink to={`/novel/${novelId}/world`}>世界观设定</NavLink>
          <NavLink to={`/novel/${novelId}/styles`}>文风</NavLink>
          <NavLink to={`/novel/${novelId}/settings`}>模型设置</NavLink>
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
        <Outlet />
      </main>
    </div>
  );
}
