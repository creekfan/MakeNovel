const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface Novel {
  id: string;
  name: string;
}

export interface OutlineNode {
  id: string;
  title: string;
  node_type: "volume" | "chapter" | "section";
  summary: string;
  status: string;
  content?: string | null;
  chapter_prompt?: string | null;
  children: OutlineNode[];
  sort_order: number;
}

export interface OutlineTree {
  novel_id: string;
  novel_title: string;
  volumes: OutlineNode[];
}

export interface Character {
  id: string;
  name: string;
  role: string;
  appearance: string;
  personality: string;
  background: string;
  abilities?: string | null;
  speech_style?: string | null;
  arc?: string | null;
  current_state?: string | null;
  relationships: { source_id: string; target_id: string; relation_type: string; description: string }[];
}

export interface WorldSetting {
  id: string;
  name: string;
  category: string;
  description: string;
  notable_features: string[];
}

export const api = {
  novels: {
    list: () => request<Novel[]>("/novels"),
    create: (name: string) => request<Novel>("/novels", { method: "POST", body: JSON.stringify({ name }) }),
    get: (id: string) => request<Novel>(`/novels/${id}`),
    delete: (id: string) => request<void>(`/novels/${id}`, { method: "DELETE" }),
  },
  outline: {
    get: (novelId: string) => request<OutlineTree>(`/novels/${novelId}/outline`),
    save: (novelId: string, data: OutlineTree) =>
      request<void>(`/novels/${novelId}/outline`, { method: "PUT", body: JSON.stringify(data) }),
    getContent: (novelId: string, sectionId: string) =>
      request<{ section_id: string; content: string }>(`/novels/${novelId}/outline/section/${sectionId}/content`),
    saveContent: (novelId: string, sectionId: string, content: string) =>
      request<void>(`/novels/${novelId}/outline/section/${sectionId}/content`, {
        method: "PUT",
        body: JSON.stringify({ content }),
      }),
  },
  characters: {
    get: (novelId: string) => request<Character[]>(`/novels/${novelId}/characters`),
    save: (novelId: string, data: Character[]) =>
      request<void>(`/novels/${novelId}/characters`, { method: "PUT", body: JSON.stringify(data) }),
    add: (novelId: string, data: Character) =>
      request<void>(`/novels/${novelId}/characters`, { method: "POST", body: JSON.stringify(data) }),
    delete: (novelId: string, charId: string) =>
      request<void>(`/novels/${novelId}/characters/${charId}`, { method: "DELETE" }),
  },
  world: {
    get: (novelId: string) => request<WorldSetting[]>(`/novels/${novelId}/world`),
    save: (novelId: string, data: WorldSetting[]) =>
      request<void>(`/novels/${novelId}/world`, { method: "PUT", body: JSON.stringify(data) }),
    add: (novelId: string, data: WorldSetting) =>
      request<void>(`/novels/${novelId}/world`, { method: "POST", body: JSON.stringify(data) }),
    delete: (novelId: string, settingId: string) =>
      request<void>(`/novels/${novelId}/world/${settingId}`, { method: "DELETE" }),
  },
  styles: {
    list: (novelId: string) =>
      request<{ id: string; name: string; created_at: string }[]>(`/novels/${novelId}/styles`),
    get: (novelId: string, styleId: string) =>
      request<{ id: string; name: string; created_at: string; content: string }>(
        `/novels/${novelId}/styles/${styleId}`,
      ),
    create: (novelId: string, name: string, content: string) =>
      request<{ id: string; name: string; created_at: string; content: string }>(
        `/novels/${novelId}/styles`,
        { method: "POST", body: JSON.stringify({ name, content }) },
      ),
    update: (novelId: string, styleId: string, name: string, content: string) =>
      request<{ id: string; name: string; created_at: string; content: string }>(
        `/novels/${novelId}/styles/${styleId}`,
        { method: "PUT", body: JSON.stringify({ name, content }) },
      ),
    delete: (novelId: string, styleId: string) =>
      request<{ ok: boolean }>(`/novels/${novelId}/styles/${styleId}`, { method: "DELETE" }),
  },
  agent: {
    run: (novelId: string, params: {
      section_id: string;
      api_key: string;
      model: string;
      base_url: string;
      temperature: number;
      max_tokens: number;
      instruction?: string;
      style_id?: string;
    }) => request<unknown>(`/novels/${novelId}/agent/run`, { method: "POST", body: JSON.stringify(params) }),
    summarize: (novelId: string, params: {
      section_id: string;
      api_key: string;
      model: string;
      base_url: string;
      content: string;
    }) => request<{
      section_id: string;
      summary: string;
      key_events: string[];
      character_state_changes: Record<string, string>;
      world_setting_changes: Record<string, string>;
    }>(`/novels/${novelId}/agent/summrize`, {
      method: "POST",
      body: JSON.stringify(params),
    }),
    runAgentStream: async (
      novelId: string,
      params: {
        section_id: string;
        api_key: string;
        model: string;
        base_url: string;
        temperature: number;
        max_tokens: number;
        instruction: string;
        style_id?: string;
      },
      onEvent: (event: Record<string, unknown>) => void,
    ) => {
      const res = await fetch(`${BASE}/novels/${novelId}/agent/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`API Error ${res.status}: ${text}`);
      }
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              onEvent(JSON.parse(line.slice(6)));
            } catch {}
          }
        }
      }
      if (buffer.startsWith("data: ")) {
        try {
          onEvent(JSON.parse(buffer.slice(6)));
        } catch {}
      }
    },
  },
};
