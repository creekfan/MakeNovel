async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  const text = await res.text();
  return text ? JSON.parse(text) : ({} as T);
}

import type { Novel, NovelListItem, Character, Relationship, Setting, OutlineNode, AIAction } from '@/types';

export const api = {
  // Novels
  listNovels: () => request<NovelListItem[]>('/novels'),
  createNovel: (data: Partial<Novel>) => request<Novel>('/novels', { method: 'POST', body: JSON.stringify(data) }),
  getNovel: (id: number) => request<Novel>(`/novels/${id}`),
  updateNovel: (id: number, data: Partial<Novel>) => request<Novel>(`/novels/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteNovel: (id: number) => request<{ ok: boolean }>(`/novels/${id}`, { method: 'DELETE' }),

  // Characters
  listCharacters: (novelId: number) => request<Character[]>(`/characters/novel/${novelId}`),
  createCharacter: (data: Partial<Character>) => request<Character>('/characters', { method: 'POST', body: JSON.stringify(data) }),
  getCharacter: (id: number) => request<Character>(`/characters/${id}`),
  updateCharacter: (id: number, data: Partial<Character>) =>
    request<Character>(`/characters/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCharacter: (id: number) => request<{ ok: boolean }>(`/characters/${id}`, { method: 'DELETE' }),
  createRelationship: (data: { source_id: number; target_id: number; relation_type: string; description: string }) =>
    request<Relationship>('/characters/relationships', { method: 'POST', body: JSON.stringify(data) }),
  deleteRelationship: (id: number) => request<{ ok: boolean }>(`/characters/relationships/${id}`, { method: 'DELETE' }),

  // Settings
  listSettings: (novelId: number) => request<Setting[]>(`/settings/novel/${novelId}`),
  createSetting: (data: Partial<Setting>) => request<Setting>('/settings', { method: 'POST', body: JSON.stringify(data) }),
  updateSetting: (id: number, data: Partial<Setting>) =>
    request<Setting>(`/settings/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSetting: (id: number) => request<{ ok: boolean }>(`/settings/${id}`, { method: 'DELETE' }),

  // Outlines
  listOutline: (novelId: number) => request<OutlineNode[]>(`/outlines/novel/${novelId}`),
  createOutlineNode: (data: Partial<OutlineNode>) => request<OutlineNode>('/outlines', { method: 'POST', body: JSON.stringify(data) }),
  updateOutlineNode: (id: number, data: Partial<OutlineNode>) =>
    request<OutlineNode>(`/outlines/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteOutlineNode: (id: number) => request<{ ok: boolean }>(`/outlines/${id}`, { method: 'DELETE' }),
  embedOutlineNode: (id: number, provider: string, model: string, apiKey: string) =>
    request<{ ok: boolean }>(`/outlines/${id}/embed`, { method: 'POST', body: JSON.stringify({ provider, model, api_key: apiKey }) }),
  summarizeOutlineNode: (id: number, provider: string, model: string, apiKey: string) =>
    request<{ ok: boolean; summary?: string }>(`/outlines/${id}/summarize`, { method: 'POST', body: JSON.stringify({ provider, model, api_key: apiKey }) }),

  // Search
  searchCharacters: (novelId: number, q: string) =>
    request<{ id: number; name: string }[]>(`/characters/search/${novelId}?q=${encodeURIComponent(q)}`),
  searchSettings: (novelId: number, q: string) =>
    request<{ id: number; name: string }[]>(`/settings/search?novel_id=${novelId}&q=${encodeURIComponent(q)}`),

  // AI
  listActions: () => request<AIAction[]>('/ai/actions'),
  generateAI: (data: {
    novel_id: number;
    scene_id?: number;
    action: string;
    selected_text?: string;
    instruction?: string;
    provider?: string;
    model?: string;
    api_key?: string;
    active_character_ids?: number[];
    active_setting_ids?: number[];
  }) => {
    return fetch(`/api/ai/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },
};
