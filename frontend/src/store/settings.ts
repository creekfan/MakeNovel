import { create } from "zustand";

const STORAGE_KEY = "novel_agent_settings";

export interface LLMSettings {
  apiKey: string;
  model: string;
  baseUrl: string;
  temperature: number;
  maxTokens: number;
}

interface SettingsState {
  settings: LLMSettings;
  load: () => void;
  save: (s: Partial<LLMSettings>) => void;
  clear: () => void;
}

const DEFAULT_SETTINGS: LLMSettings = {
  apiKey: "",
  model: "deepseek-chat",
  baseUrl: "https://api.deepseek.com",
  temperature: 0.7,
  maxTokens: 10000,
};

function encodeSettings(s: LLMSettings): string {
  return btoa(unescape(encodeURIComponent(JSON.stringify(s))));
}

function decodeSettings(encoded: string): LLMSettings {
  try {
    return JSON.parse(decodeURIComponent(escape(atob(encoded))));
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: { ...DEFAULT_SETTINGS },
  load: () => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      set({ settings: decodeSettings(raw) });
    }
  },
  save: (partial) => {
    const next = { ...get().settings, ...partial };
    set({ settings: next });
    localStorage.setItem(STORAGE_KEY, encodeSettings(next));
  },
  clear: () => {
    localStorage.removeItem(STORAGE_KEY);
    set({ settings: { ...DEFAULT_SETTINGS } });
  },
}));
