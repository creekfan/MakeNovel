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

async function streamSSE(
  path: string,
  body: unknown,
  onEvent: (event: Record<string, unknown>) => void,
): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error ${res.status}: ${text}`);
  }
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const flush = (line: string) => {
    if (line.startsWith("data: ")) {
      try {
        onEvent(JSON.parse(line.slice(6)));
      } catch {}
    }
  };
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) flush(line);
  }
  if (buffer) flush(buffer);
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

export interface Snapshot {
  id: string;
  source_type: "character" | "setting" | "free";
  source_id?: string | null;
  name: string;
  label: string;
  category: string;
  fields: Record<string, unknown>;
  created_at?: string | null;
}

export interface NovelEvent {
  id: string;
  title: string;
  description: string;
  time_label?: string | null;
  created_at?: string | null;
}

export interface CanvasPlacement {
  placement_id: string;
  entity_type: "snapshot" | "event";
  entity_id: string;
  x: number;
  y: number;
}

export interface CanvasEdge {
  id: string;
  source: string;
  target: string;
  kind: "note_to_event" | "event_to_event" | "event_to_note_change";
  source_handle?: string | null;
  target_handle?: string | null;
}

export interface CanvasData {
  node_id: string;
  nodes: CanvasPlacement[];
  edges: CanvasEdge[];
  viewport?: { x: number; y: number; zoom: number } | null;
}

export interface SnapshotPlacement {
  node_id: string;
  node_title: string;
  placement_id: string;
  x: number;
  y: number;
}

export interface AgentLogSummary {
  run_id: string;
  section_id: string;
  section_title: string;
  instruction: string;
  model: string;
  status: string;
  started_at: string;
  finished_at: string;
  event_count: number;
  final_len: number;
}

export interface AgentLogEvent {
  step: string;
  status: string;
  message?: string;
  tool?: string;
  input?: string;
  output?: string;
  final_content?: string;
}

export interface AgentLog extends AgentLogSummary {
  events: AgentLogEvent[];
  final_content: string;
}

export interface WritingPlan {
  involved_characters: string[];
  involved_settings: string[];
  prev_recap: string;
  this_goal: string;
  next_setup: string;
  beats: string[];
}

export interface ReviewIssue {
  type: string;
  severity: string;
  description: string;
  suggestion: string;
}

export interface ReviewResult {
  ok: boolean;
  issues: ReviewIssue[];
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
    assistant: (novelId: string, params: {
      messages: { role: "user" | "assistant"; content: string }[];
      api_key: string;
      model: string;
      base_url: string;
      temperature: number;
    }) => request<{ reply: string }>(`/novels/${novelId}/outline/assistant`, {
      method: "POST",
      body: JSON.stringify(params),
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
  snapshots: {
    list: (novelId: string) => request<Snapshot[]>(`/novels/${novelId}/snapshots`),
    placements: (novelId: string, snapshotId: string) =>
      request<SnapshotPlacement[]>(`/novels/${novelId}/snapshots/${snapshotId}/placements`),
    add: (novelId: string, data: Snapshot & { create_master?: boolean }) =>
      request<{ ok: boolean; id: string; source_id?: string }>(`/novels/${novelId}/snapshots`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (novelId: string, snapshotId: string, data: Snapshot) =>
      request<{ ok: boolean }>(`/novels/${novelId}/snapshots/${snapshotId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (novelId: string, snapshotId: string) =>
      request<{ ok: boolean }>(`/novels/${novelId}/snapshots/${snapshotId}`, { method: "DELETE" }),
  },
  events: {
    list: (novelId: string) => request<NovelEvent[]>(`/novels/${novelId}/events`),
    add: (novelId: string, data: NovelEvent) =>
      request<{ ok: boolean; id: string }>(`/novels/${novelId}/events`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (novelId: string, eventId: string, data: NovelEvent) =>
      request<{ ok: boolean }>(`/novels/${novelId}/events/${eventId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (novelId: string, eventId: string) =>
      request<{ ok: boolean }>(`/novels/${novelId}/events/${eventId}`, { method: "DELETE" }),
  },
  canvas: {
    get: (novelId: string, nodeId: string) =>
      request<CanvasData>(`/novels/${novelId}/canvas/${nodeId}`),
    save: (novelId: string, nodeId: string, data: CanvasData) =>
      request<{ ok: boolean }>(`/novels/${novelId}/canvas/${nodeId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
  },
  agent: {
    logs: {
      list: (novelId: string) => request<AgentLogSummary[]>(`/novels/${novelId}/agent/logs`),
      get: (novelId: string, runId: string) =>
        request<AgentLog>(`/novels/${novelId}/agent/logs/${runId}`),
      delete: (novelId: string, runId: string) =>
        request<{ ok: boolean }>(`/novels/${novelId}/agent/logs/${runId}`, { method: "DELETE" }),
    },
    planStream: (
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
    ) => streamSSE(`/novels/${novelId}/agent/plan`, params, onEvent),
    resumeStream: (
      novelId: string,
      params: {
        thread_id: string;
        action: "confirm_plan" | "revise" | "polish";
        api_key: string;
        model: string;
        base_url: string;
        temperature: number;
        max_tokens: number;
        edited_plan?: Record<string, unknown> | null;
        edited_draft?: string | null;
      },
      onEvent: (event: Record<string, unknown>) => void,
    ) => streamSSE(`/novels/${novelId}/agent/resume`, params, onEvent),
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
  },
};
