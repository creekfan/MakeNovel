import { create } from "zustand";

const KEY = "novel_agent_theme";

interface ThemeState {
  dark: boolean;
  toggle: () => void;
  load: () => void;
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  dark: false,
  toggle: () => {
    const next = !get().dark;
    set({ dark: next });
    localStorage.setItem(KEY, next ? "dark" : "light");
    applyTheme(next);
  },
  load: () => {
    const val = localStorage.getItem(KEY);
    const prefersDark = val === "dark" || (!val && window.matchMedia("(prefers-color-scheme: dark)").matches);
    set({ dark: prefersDark });
    applyTheme(prefersDark);
  },
}));

function applyTheme(dark: boolean) {
  document.body.classList.toggle("dark", dark);
}
