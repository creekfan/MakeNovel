export type NodeKind = "sticky" | "event";

export type EdgeKind = "note_to_event" | "event_to_event" | "event_to_note_change";

export function connectionKind(srcKind: NodeKind, tgtKind: NodeKind): EdgeKind | null {
  if (srcKind === "sticky" && tgtKind === "event") return "note_to_event";
  if (srcKind === "event" && tgtKind === "event") return "event_to_event";
  if (srcKind === "event" && tgtKind === "sticky") return "event_to_note_change";
  return null;
}

export const GRID_COLS = 6;
export const GRID_STEP = 44;

export interface XY {
  x: number;
  y: number;
}

export function nextNodePosition(center: XY, count: number): XY {
  const col = count % GRID_COLS;
  const row = Math.floor(count / GRID_COLS);
  return {
    x: center.x + col * GRID_STEP - ((GRID_COLS - 1) * GRID_STEP) / 2,
    y: center.y + row * GRID_STEP,
  };
}
