export interface Novel {
  id: number;
  title: string;
  description: string;
  genre: string;
  style_notes: string;
  word_count_goal: number;
  chapter_count: number;
  total_word_count: number;
  created_at: string;
  updated_at: string;
}

export interface NovelListItem {
  id: number;
  title: string;
  description: string;
  genre: string;
  chapter_count: number;
  total_word_count: number;
  created_at: string;
  updated_at: string;
}

export interface Chapter {
  id: number;
  novel_id: number;
  title: string;
  chapter_number: number;
  status: 'draft' | 'revising' | 'done';
  content: string;
  summary: string;
  character_snapshot: Record<string, unknown>;
  plot_points: string[];
  word_count: number;
  chapter_prompt: string;
  created_at: string;
  updated_at: string;
}

export interface ChapterListItem {
  id: number;
  novel_id: number;
  title: string;
  chapter_number: number;
  status: string;
  summary: string;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export interface Character {
  id: number;
  novel_id: number;
  name: string;
  aliases: string[];
  role: 'protagonist' | 'antagonist' | 'supporting' | 'minor';
  profile: CharacterProfile;
  arc: string;
  avatar_color: string;
  relationships: Relationship[];
  created_at: string;
  updated_at: string;
}

export interface CharacterProfile {
  appearance?: string;
  age?: string;
  personality?: string;
  background?: string;
  speech_style?: string;
  [key: string]: string | undefined;
}

export interface Relationship {
  id: number;
  source_id: number;
  target_id: number;
  target_name: string;
  relation_type: string;
  description: string;
}

export interface Setting {
  id: number;
  novel_id: number;
  name: string;
  category: string;
  location_type: string;
  description: string;
  notable_features: string[];
  chapters_featured: number[];
  created_at: string;
  updated_at: string;
}

export interface OutlineNode {
  id: number;
  novel_id: number;
  parent_id: number | null;
  node_type: string;
  title: string;
  summary: string;
  notes: string;
  status: string;
  sort_order: number;
  assigned_chapter_id: number | null;
  content: string;
  children: OutlineNode[];
  created_at: string;
  updated_at: string;
}

export interface AIAction {
  action: string;
  label: string;
  description: string;
  requires_text: boolean;
}
