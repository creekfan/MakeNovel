import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Novel, NovelListItem, Character, Setting, OutlineNode } from '@/types';
import { api } from '@/lib/api';

interface NovelStore {
  novels: NovelListItem[];
  loading: boolean;
  error: string | null;
  loadNovels: () => Promise<void>;
  createNovel: (data: { title: string; description?: string; genre?: string }) => Promise<Novel>;
  deleteNovel: (id: number) => Promise<void>;
}

export const useNovelStore = create<NovelStore>((set) => ({
  novels: [],
  loading: false,
  error: null,
  loadNovels: async () => {
    set({ loading: true, error: null });
    try {
      const novels = await api.listNovels();
      set({ novels, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },
  createNovel: async (data) => {
    const novel = await api.createNovel(data);
    set((s) => ({ novels: [{
      id: novel.id, title: novel.title, description: novel.description,
      genre: novel.genre, chapter_count: 0, total_word_count: 0,
      created_at: novel.created_at, updated_at: novel.updated_at,
    }, ...s.novels] }));
    return novel;
  },
  deleteNovel: async (id) => {
    await api.deleteNovel(id);
    set((s) => ({ novels: s.novels.filter((n) => n.id !== id) }));
  },
}));

interface CurrentNovelStore {
  novel: Novel | null;
  characters: Character[];
  settings: Setting[];
  outline: OutlineNode[];
  loading: boolean;
  notFound: boolean;
  loadNovel: (id: number) => Promise<void>;
  loadCharacters: () => Promise<void>;
  loadSettings: () => Promise<void>;
  loadOutline: () => Promise<void>;
}

export const useCurrentNovelStore = create<CurrentNovelStore>((set, get) => ({
  novel: null,
  characters: [],
  settings: [],
  outline: [],
  loading: false,
  notFound: false,
  loadNovel: async (id) => {
    set({ loading: true, notFound: false });
    try {
      const novel = await api.getNovel(id);
      set({ novel, loading: false });
    } catch {
      set({ novel: null, loading: false, notFound: true });
    }
  },
  loadCharacters: async () => {
    const novel = get().novel;
    if (!novel) return;
    const characters = await api.listCharacters(novel.id);
    set({ characters });
  },
  loadSettings: async () => {
    const novel = get().novel;
    if (!novel) return;
    const settings = await api.listSettings(novel.id);
    set({ settings });
  },
  loadOutline: async () => {
    const novel = get().novel;
    if (!novel) return;
    const outline = await api.listOutline(novel.id);
    set({ outline });
  },
}));

interface SettingsStore {
  provider: string;
  openaiKey: string;
  openaiModel: string;
  anthropicKey: string;
  anthropicModel: string;
  ollamaUrl: string;
  ollamaModel: string;
  deepseekKey: string;
  deepseekModel: string;
  geminiKey: string;
  geminiModel: string;
  recommendProvider: string;
  recommendModel: string;
  setProvider: (p: string) => void;
  setOpenaiKey: (k: string) => void;
  setOpenaiModel: (m: string) => void;
  setAnthropicKey: (k: string) => void;
  setAnthropicModel: (m: string) => void;
  setOllamaUrl: (u: string) => void;
  setOllamaModel: (m: string) => void;
  setDeepseekKey: (k: string) => void;
  setDeepseekModel: (m: string) => void;
  setGeminiKey: (k: string) => void;
  setGeminiModel: (m: string) => void;
  setRecommendProvider: (p: string) => void;
  setRecommendModel: (m: string) => void;
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      provider: 'openai',
      openaiKey: '',
      openaiModel: 'gpt-4o',
      anthropicKey: '',
      anthropicModel: 'claude-3-5-sonnet-20240620',
      ollamaUrl: 'http://localhost:11434',
      ollamaModel: 'llama3',
      deepseekKey: '',
      deepseekModel: 'deepseek-chat',
      geminiKey: '',
      geminiModel: 'gemini-2.5-flash',
      recommendProvider: 'gemini',
      recommendModel: '',
      setProvider: (provider) => set({ provider }),
      setOpenaiKey: (openaiKey) => set({ openaiKey }),
      setOpenaiModel: (openaiModel) => set({ openaiModel }),
      setAnthropicKey: (anthropicKey) => set({ anthropicKey }),
      setAnthropicModel: (anthropicModel) => set({ anthropicModel }),
      setOllamaUrl: (ollamaUrl) => set({ ollamaUrl }),
      setOllamaModel: (ollamaModel) => set({ ollamaModel }),
      setDeepseekKey: (deepseekKey) => set({ deepseekKey }),
      setDeepseekModel: (deepseekModel) => set({ deepseekModel }),
      setGeminiKey: (geminiKey) => set({ geminiKey }),
      setGeminiModel: (geminiModel) => set({ geminiModel }),
      setRecommendProvider: (recommendProvider) => set({ recommendProvider }),
      setRecommendModel: (recommendModel) => set({ recommendModel }),
    }),
    {
      name: 'makenovel-settings',
      partialize: (state) => {
        const { setProvider, setOpenaiKey, setOpenaiModel, setAnthropicKey, setAnthropicModel, setOllamaUrl, setOllamaModel, setDeepseekKey, setDeepseekModel, setGeminiKey, setGeminiModel, setRecommendProvider, setRecommendModel, ...data } = state;
        return data as Record<string, unknown>;
      },
    }
  )
);
