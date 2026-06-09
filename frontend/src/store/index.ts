import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Novel, NovelListItem, Chapter, Character, Setting, OutlineNode } from '@/types';
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
  chapters: Chapter[];
  characters: Character[];
  settings: Setting[];
  outline: OutlineNode[];
  loading: boolean;
  notFound: boolean;
  loadNovel: (id: number) => Promise<void>;
  loadChapters: () => Promise<void>;
  loadCharacters: () => Promise<void>;
  loadSettings: () => Promise<void>;
  loadOutline: () => Promise<void>;
  addChapter: (data: { title: string; chapter_number: number }) => Promise<Chapter>;
  deleteChapter: (id: number) => Promise<void>;
}

export const useCurrentNovelStore = create<CurrentNovelStore>((set, get) => ({
  novel: null,
  chapters: [],
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
  loadChapters: async () => {
    const novel = get().novel;
    if (!novel) return;
    const chapters = await api.listChapters(novel.id);
    set({ chapters: chapters.map((c) => ({ ...c, content: '', character_snapshot: {}, plot_points: [], chapter_prompt: '' })) as Chapter[] });
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
  addChapter: async (data) => {
    const novel = get().novel;
    if (!novel) throw new Error('No novel loaded');
    const chapter = await api.createChapter({ novel_id: novel.id, ...data });
    set((s) => ({ chapters: [...s.chapters, chapter] }));
    return chapter;
  },
  deleteChapter: async (id) => {
    await api.deleteChapter(id);
    set((s) => ({ chapters: s.chapters.filter((c) => c.id !== id) }));
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
  setProvider: (p: string) => void;
  setOpenaiKey: (k: string) => void;
  setOpenaiModel: (m: string) => void;
  setAnthropicKey: (k: string) => void;
  setAnthropicModel: (m: string) => void;
  setOllamaUrl: (u: string) => void;
  setOllamaModel: (m: string) => void;
  setDeepseekKey: (k: string) => void;
  setDeepseekModel: (m: string) => void;
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
      setProvider: (provider) => set({ provider }),
      setOpenaiKey: (openaiKey) => set({ openaiKey }),
      setOpenaiModel: (openaiModel) => set({ openaiModel }),
      setAnthropicKey: (anthropicKey) => set({ anthropicKey }),
      setAnthropicModel: (anthropicModel) => set({ anthropicModel }),
      setOllamaUrl: (ollamaUrl) => set({ ollamaUrl }),
      setOllamaModel: (ollamaModel) => set({ ollamaModel }),
      setDeepseekKey: (deepseekKey) => set({ deepseekKey }),
      setDeepseekModel: (deepseekModel) => set({ deepseekModel }),
    }),
    {
      name: 'makenovel-settings',
      partialize: (state) => {
        const { setProvider, setOpenaiKey, setOpenaiModel, setAnthropicKey, setAnthropicModel, setOllamaUrl, setOllamaModel, setDeepseekKey, setDeepseekModel, ...data } = state;
        return data as Record<string, unknown>;
      },
    }
  )
);
