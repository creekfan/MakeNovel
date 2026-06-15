import { Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import HomePage from "./pages/HomePage";
import NovelLayout from "./pages/NovelLayout";
import OutlinePage from "./pages/OutlinePage";
import EditorPage from "./pages/EditorPage";
import CharactersPage from "./pages/CharactersPage";
import WorldPage from "./pages/WorldPage";
import SettingsPage from "./pages/SettingsPage";
import { useSettingsStore } from "./store/settings";
import { useThemeStore } from "./store/theme";

export default function App() {
  const load = useSettingsStore((s) => s.load);
  const loadTheme = useThemeStore((s) => s.load);
  useEffect(() => { load(); loadTheme(); }, [load, loadTheme]);

  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/novel/:novelId" element={<NovelLayout />}>
        <Route index element={<OutlinePage />} />
        <Route path="outline" element={<OutlinePage />} />
        <Route path="editor/:sectionId" element={<EditorPage />} />
        <Route path="characters" element={<CharactersPage />} />
        <Route path="world" element={<WorldPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
