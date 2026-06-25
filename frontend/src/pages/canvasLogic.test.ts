import { describe, it, expect } from "vitest";
import { connectionKind, nextNodePosition, GRID_COLS } from "./canvasLogic";

describe("connectionKind", () => {
  it("便签 → 事件", () => {
    expect(connectionKind("sticky", "event")).toBe("note_to_event");
  });
  it("事件 → 事件", () => {
    expect(connectionKind("event", "event")).toBe("event_to_event");
  });
  it("事件 → 便签（变化，虚线）", () => {
    expect(connectionKind("event", "sticky")).toBe("event_to_note_change");
  });
  it("便签 → 便签 非法", () => {
    expect(connectionKind("sticky", "sticky")).toBeNull();
  });
});

describe("nextNodePosition (修复节点叠放导致只连上层节点的 bug)", () => {
  const center = { x: 500, y: 300 };

  it("连续放置的节点位置互不相同", () => {
    const seen = new Set<string>();
    for (let i = 0; i < 60; i++) {
      const p = nextNodePosition(center, i);
      const key = `${p.x},${p.y}`;
      expect(seen.has(key)).toBe(false);
      seen.add(key);
    }
    expect(seen.size).toBe(60);
  });

  it("不会把所有节点堆叠到同一坐标（旧 bug 回归）", () => {
    const p0 = nextNodePosition(center, 0);
    const p1 = nextNodePosition(center, 1);
    expect(p0.x === p1.x && p0.y === p1.y).toBe(false);
  });

  it("按网格换行", () => {
    const first = nextNodePosition(center, 0);
    const wrapped = nextNodePosition(center, GRID_COLS);
    expect(wrapped.x).toBe(first.x);
    expect(wrapped.y).toBeGreaterThan(first.y);
  });
});
