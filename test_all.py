import sys
import json
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
PASS = 0
FAIL = 0

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  [PASS] {name}")
        PASS += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        FAIL += 1

print("=" * 50)
print(" NovelAgent Test Suite (LangChain)")
print("=" * 50)

novel_id = None

# ─── 1. Health ───
print("\n--- 1. Health Check ---")
def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
test("GET /api/health", test_health)

# ─── 2. Novel CRUD ───
print("\n--- 2. Novel CRUD ---")
def test_create_novel():
    global novel_id
    r = client.post("/api/novels", json={"name": "TestNovel"})
    assert r.status_code == 201, f"status={r.status_code}, body={r.text}"
    data = r.json()
    assert data["name"] == "TestNovel"
    assert "id" in data
    novel_id = data["id"]
test("POST /api/novels (create)", test_create_novel)

def test_list_novels():
    r = client.get("/api/novels")
    assert r.status_code == 200
    assert any(n["id"] == novel_id for n in r.json())
test("GET /api/novels (list)", test_list_novels)

def test_get_novel():
    r = client.get(f"/api/novels/{novel_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "TestNovel"
test("GET /api/novels/:id", test_get_novel)

# ─── 3. Outline ───
print("\n--- 3. Outline CRUD ---")
def test_get_outline_empty():
    r = client.get(f"/api/novels/{novel_id}/outline")
    assert r.status_code == 200
    assert r.json()["volumes"] == []
test("GET outline (empty)", test_get_outline_empty)

OUTLINE = {
    "novel_id": novel_id,
    "novel_title": "TestNovel",
    "volumes": [{
        "id": "vol-1",
        "title": "Vol 1",
        "node_type": "volume",
        "summary": "First volume",
        "status": "planned",
        "sort_order": 1.0,
        "children": [{
            "id": "ch-1",
            "title": "Chapter 1",
            "node_type": "chapter",
            "summary": "First chapter",
            "status": "planned",
            "sort_order": 1.0,
            "children": [{
                "id": "sec-1-1",
                "title": "Section 1",
                "node_type": "section",
                "summary": "Opening scene",
                "status": "planned",
                "sort_order": 1.0,
                "children": []
            }]
        }]
    }]
}

def test_save_outline():
    r = client.put(f"/api/novels/{novel_id}/outline", json=OUTLINE)
    assert r.status_code == 200
test("PUT outline (save)", test_save_outline)

def test_get_outline_saved():
    r = client.get(f"/api/novels/{novel_id}/outline")
    assert r.status_code == 200
    data = r.json()
    assert len(data["volumes"]) == 1
    assert data["volumes"][0]["children"][0]["children"][0]["id"] == "sec-1-1"
test("GET outline (verify)", test_get_outline_saved)

# ─── 4. Section Content ───
print("\n--- 4. Section Content ---")

def test_outline_delete_cascades():
    """删除大纲节时级联清除：正文内容、摘要、画板"""
    # 临时添加一节到现有大纲
    outline = client.get(f"/api/novels/{novel_id}/outline").json()
    outline["volumes"][0]["children"][0]["children"].append({
        "id": "sec-cleanup", "title": "临时节", "node_type": "section",
        "summary": "测试", "status": "planned", "children": [], "sort_order": 99
    })
    r = client.put(f"/api/novels/{novel_id}/outline", json=outline)
    assert r.status_code == 200
    # 写入 body
    client.put(f"/api/novels/{novel_id}/outline/section/sec-cleanup/content", json={"content":"临时正文"})
    assert len(client.get(f"/api/novels/{novel_id}/outline/section/sec-cleanup/content").json()["content"]) > 0
    # 写入 summary
    summaries = client.get(f"/api/novels/{novel_id}/summaries").json() if hasattr(client.get(f"/api/novels/{novel_id}/summaries"), "json") else {}
    # 直接用 storage 写入 summary
    from backend import storage as st
    ss = st.get_summaries(novel_id)
    ss.append({"section_id": "sec-cleanup", "section_title": "临时节", "summary": "test summary"})
    st.save_summaries(novel_id, ss)
    assert any(s["section_id"] == "sec-cleanup" for s in st.get_summaries(novel_id))
    # 画板
    st.save_canvas(novel_id, "sec-cleanup", {"node_id":"sec-cleanup","nodes":[{"placement_id":"px","entity_type":"event","entity_id":"ev-1","x":0,"y":0}],"edges":[]})
    assert len(st.get_canvas(novel_id, "sec-cleanup")["nodes"]) == 1
    # 删除：重新保存不含该节的大纲
    outline["volumes"][0]["children"][0]["children"] = [c for c in outline["volumes"][0]["children"][0]["children"] if c["id"] != "sec-cleanup"]
    r = client.put(f"/api/novels/{novel_id}/outline", json=outline)
    assert r.status_code == 200
    # 验证正文已清
    assert client.get(f"/api/novels/{novel_id}/outline/section/sec-cleanup/content").json()["content"] == ""
    # 验证摘要已清
    assert not any(s["section_id"] == "sec-cleanup" for s in st.get_summaries(novel_id))
    # 验证画板已清（回到默认空）
    assert len(st.get_canvas(novel_id, "sec-cleanup")["nodes"]) == 0
test("Outline delete cascades: content + summary + canvas cleanup", test_outline_delete_cascades)
def test_save_content():
    r = client.put(f"/api/novels/{novel_id}/outline/section/sec-1-1/content",
                   json={"content": "It was a dark and stormy night..."})
    assert r.status_code == 200
test("PUT section content", test_save_content)

def test_get_content():
    r = client.get(f"/api/novels/{novel_id}/outline/section/sec-1-1/content")
    assert r.status_code == 200
    assert r.json()["content"] == "It was a dark and stormy night..."
test("GET section content", test_get_content)

def test_get_empty_content():
    r = client.get(f"/api/novels/{novel_id}/outline/section/nonexist/content")
    assert r.status_code == 200
    assert r.json()["content"] == ""
test("GET empty content", test_get_empty_content)

def test_outline_assistant_no_key():
    r = client.post(f"/api/novels/{novel_id}/outline/assistant", json={
        "messages": [{"role": "user", "content": "hi"}],
        "api_key": "",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.7,
    })
    assert r.status_code == 400
test("POST outline/assistant (empty key => 400)", test_outline_assistant_no_key)

def test_outline_assistant_empty_msgs():
    r = client.post(f"/api/novels/{novel_id}/outline/assistant", json={
        "messages": [],
        "api_key": "sk-test",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.7,
    })
    assert r.status_code == 400
test("POST outline/assistant (empty messages => 400)", test_outline_assistant_empty_msgs)

# ─── 5. Characters ───
print("\n--- 5. Characters CRUD ---")
def test_get_chars_empty():
    r = client.get(f"/api/novels/{novel_id}/characters")
    assert r.status_code == 200
    assert r.json() == []
test("GET characters (empty)", test_get_chars_empty)

def test_add_char():
    r = client.post(f"/api/novels/{novel_id}/characters", json={
        "id": "char-001", "name": "Alice", "role": "protagonist",
        "appearance": "tall, dark hair", "personality": "brave and kind",
        "background": "orphan from the north", "relationships": []
    })
    assert r.status_code == 200
test("POST character", test_add_char)

def test_add_char2():
    r = client.post(f"/api/novels/{novel_id}/characters", json={
        "id": "char-002", "name": "Bob", "role": "antagonist",
        "appearance": "short, red eyes", "personality": "cunning",
        "background": "dark lord",
        "relationships": [{"source_id": "char-002", "target_id": "char-001",
                           "relation_type": "enemy", "description": "sworn enemy"}]
    })
    assert r.status_code == 200
test("POST character 2", test_add_char2)

def test_get_chars():
    r = client.get(f"/api/novels/{novel_id}/characters")
    assert r.status_code == 200
    assert len(r.json()) == 2
test("GET characters (verify 2)", test_get_chars)

# ─── 6. World Settings ───
print("\n--- 6. World Settings CRUD ---")
def test_add_world():
    r = client.post(f"/api/novels/{novel_id}/world", json={
        "id": "ws-001", "name": "Magic System", "category": "rule",
        "description": "Five elements magic",
        "notable_features": ["fire", "water", "earth", "wind", "void"]
    })
    assert r.status_code == 200
test("POST world setting", test_add_world)

def test_get_world():
    r = client.get(f"/api/novels/{novel_id}/world")
    assert r.status_code == 200
    ws = r.json()
    assert len(ws) == 1
    assert ws[0]["notable_features"] == ["fire", "water", "earth", "wind", "void"]
test("GET world (verify)", test_get_world)

# ─── 7. LangChain Tool Unit Tests ───
print("\n--- 7. LangChain Tool Unit Tests ---")
def test_tools_import():
    from backend.app.tools import get_all_tools
    tools = get_all_tools(novel_id)
    assert len(tools) == 6
    names = [t.name for t in tools]
    assert "get_outline" in names
    assert "get_characters" in names
    assert "get_world_settings" in names
    assert "get_summaries" in names
    assert "search_memory" in names
    assert "finish" in names
    # 上下文工具不再向 LLM 暴露 novel_id 参数
    outline_tool = next(t for t in tools if t.name == "get_outline")
    assert "novel_id" not in outline_tool.args_schema.model_fields
test("get_all_tools(novel_id) returns 6 bound tools", test_tools_import)

def test_get_outline_tool():
    from backend.app.tools import GetOutlineTool
    tool = GetOutlineTool(novel_id=novel_id)
    result = tool._run()
    assert "TestNovel" in result
    assert "Sec" in result or "Opening" in result or result, f"Unexpected: {result[:100]}"
test("GetOutlineTool returns outline (bound)", test_get_outline_tool)

def test_get_characters_tool():
    from backend.app.tools import GetCharactersTool
    tool = GetCharactersTool(novel_id=novel_id)
    result = tool._run()
    assert "Alice" in result
    assert "protagonist" in result
test("GetCharactersTool returns characters (bound)", test_get_characters_tool)

def test_get_world_tool():
    from backend.app.tools import GetWorldSettingsTool
    tool = GetWorldSettingsTool(novel_id=novel_id)
    result = tool._run()
    assert "Magic" in result or "magic" in result.lower()
test("GetWorldSettingsTool returns settings (bound)", test_get_world_tool)

def test_get_summaries_tool():
    from backend.app.tools import GetSummariesTool
    tool = GetSummariesTool(novel_id=novel_id)
    result = tool._run()
    assert result and len(result) > 0
test("GetSummariesTool returns summaries (bound)", test_get_summaries_tool)

def test_read_does_not_create_dir():
    # 读取不存在的小说不应再创建空目录（修复幻觉 novel_id 产生垃圾目录的问题）
    from pathlib import Path
    from backend.app.tools import GetOutlineTool
    bogus = "bogus-hallucinated-id-xyz"
    data_dir = Path("backend/data") / bogus
    assert not data_dir.exists()
    result = GetOutlineTool(novel_id=bogus)._run()
    assert result == "暂无大纲"
    assert not data_dir.exists(), "读操作不应创建小说目录"
test("Tool read does not create junk dir", test_read_does_not_create_dir)

def test_agent_import():
    from backend.app.agent import NovelAgent
    import inspect
    assert inspect.isasyncgenfunction(NovelAgent.start_plan)
    assert inspect.isasyncgenfunction(NovelAgent.resume)
test("NovelAgent has start_plan/resume async generators", test_agent_import)

# ─── 8. Agent Endpoint ───
print("\n--- 8. Agent Endpoint ---")
def test_agent_no_key():
    r = client.post(f"/api/novels/{novel_id}/agent/plan", json={
        "section_id": "sec-1-1",
        "api_key": "",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.7,
        "max_tokens": 10000,
        "instruction": "test"
    })
    assert r.status_code == 400
test("POST agent/plan (empty key => 400)", test_agent_no_key)

def test_agent_invalid_key():
    """Pipeline responds with SSE error event when LLM call fails"""
    r = client.post(f"/api/novels/{novel_id}/agent/plan", json={
        "section_id": "sec-1-1",
        "api_key": "sk-fake-key",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.7,
        "max_tokens": 10000,
        "instruction": "test instruction"
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    events = []
    for line in r.text.strip().split("\n"):
        if line.startswith("data:"):
            try:
                events.append(json.loads(line[5:].strip()))
            except json.JSONDecodeError:
                pass
    assert len(events) > 0, f"Expected SSE events, got: {r.text[:300]}"
    error_events = [e for e in events if e.get("step") == "error"]
    if error_events:
        print(f"    (pipeline returned error as expected: {error_events[0].get('message', '')[:80]})")
test("POST agent/plan (invalid key => SSE events)", test_agent_invalid_key)

# ─── 9. RAG Memory ───
print("\n--- 9. RAG Memory ---")
def test_embed_search():
    from backend.app.memory import embed_section, search_sections
    embed_section(novel_id, "sec-1-1", "Section 1", "It was a dark and stormy night...")
    results = search_sections(novel_id, "stormy night", top_k=3)
    assert isinstance(results, list)
test("embed_section + search_sections", test_embed_search)

# ─── 10. Summarize ───
print("\n--- 10. Summarize Endpoint ---")
def test_summarize_no_key():
    r = client.post(f"/api/novels/{novel_id}/agent/summrize", json={
        "section_id": "sec-1-1",
        "api_key": "",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "content": "Test content here"
    })
    assert r.status_code == 400
test("POST summrize (empty key => 400)", test_summarize_no_key)

def test_summarize_empty():
    r = client.post(f"/api/novels/{novel_id}/agent/summrize", json={
        "section_id": "sec-1-1",
        "api_key": "fake",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "content": ""
    })
    assert r.status_code == 400
test("POST summrize (empty content => 400)", test_summarize_empty)

# ─── 11. Events / Snapshots / Canvas ───
print("\n--- 11. Events / Snapshots / Canvas ---")
def test_events_crud():
    r = client.post(f"/api/novels/{novel_id}/events", json={
        "id": "ev-1", "title": "决战", "description": "主角对决反派", "time_label": "第三卷"
    })
    assert r.status_code == 200, r.text
    r = client.get(f"/api/novels/{novel_id}/events")
    assert r.status_code == 200
    assert any(e["id"] == "ev-1" for e in r.json())
    r = client.put(f"/api/novels/{novel_id}/events/ev-1", json={
        "id": "ev-1", "title": "最终决战", "description": "x", "time_label": "尾声"
    })
    assert r.status_code == 200
    r = client.get(f"/api/novels/{novel_id}/events")
    assert next(e for e in r.json() if e["id"] == "ev-1")["title"] == "最终决战"
test("Events CRUD", test_events_crud)

def test_snapshot_sync_master():
    r = client.post(f"/api/novels/{novel_id}/snapshots", json={
        "id": "snap-1", "source_type": "character", "source_id": None,
        "name": "Carol", "label": "初登场",
        "fields": {"role": "supporting", "personality": "shy"},
        "create_master": True
    })
    assert r.status_code == 200, r.text
    chars = client.get(f"/api/novels/{novel_id}/characters").json()
    assert any(c["name"] == "Carol" for c in chars), "master card not synced"
    snaps = client.get(f"/api/novels/{novel_id}/snapshots").json()
    assert any(s["id"] == "snap-1" for s in snaps)
test("Snapshot create syncs master card", test_snapshot_sync_master)

def test_snapshot_no_sync_master():
    # existing-character snapshot without create_master must NOT add a master
    before = len(client.get(f"/api/novels/{novel_id}/characters").json())
    r = client.post(f"/api/novels/{novel_id}/snapshots", json={
        "id": "snap-2", "source_type": "character", "source_id": "char-001",
        "name": "Alice", "label": "重伤后",
        "fields": {"current_state": "wounded"}, "create_master": False
    })
    assert r.status_code == 200
    after = len(client.get(f"/api/novels/{novel_id}/characters").json())
    assert before == after, "should not create master when create_master=False"
test("Snapshot without create_master keeps history", test_snapshot_no_sync_master)

def test_canvas_save_get():
    r = client.put(f"/api/novels/{novel_id}/canvas/vol-1", json={
        "node_id": "vol-1",
        "nodes": [
            {"placement_id": "pl-1", "entity_type": "snapshot", "entity_id": "snap-1", "x": 10, "y": 20},
            {"placement_id": "pl-2", "entity_type": "event", "entity_id": "ev-1", "x": 100, "y": 200},
        ],
        "edges": [
            {"id": "e-1", "source": "pl-1", "target": "pl-2", "kind": "note_to_event",
             "source_handle": "right", "target_handle": "left"}
        ],
        "viewport": {"x": 0, "y": 0, "zoom": 1}
    })
    assert r.status_code == 200, r.text
    data = client.get(f"/api/novels/{novel_id}/canvas/vol-1").json()
    assert len(data["nodes"]) == 2
    assert data["edges"][0]["kind"] == "note_to_event"
    assert data["edges"][0]["source_handle"] == "right"
    assert data["edges"][0]["target_handle"] == "left"
test("Canvas save + get", test_canvas_save_get)

def test_canvas_empty():
    data = client.get(f"/api/novels/{novel_id}/canvas/ch-1").json()
    assert data["nodes"] == [] and data["edges"] == []
test("Canvas empty default", test_canvas_empty)

def test_snapshot_placements():
    r = client.get(f"/api/novels/{novel_id}/snapshots/snap-1/placements")
    assert r.status_code == 200
    pls = r.json()
    assert any(p["node_id"] == "vol-1" and p["placement_id"] == "pl-1" for p in pls)
    assert pls[0]["node_title"] == "Vol 1"
test("Snapshot placements reverse-lookup", test_snapshot_placements)

# ─── 12. Events / Snapshots / Canvas (extended) ───
print("\n--- 12. Events / Snapshots / Canvas (extended) ---")
def test_event_get_and_404():
    r = client.get(f"/api/novels/{novel_id}/events/ev-1")
    assert r.status_code == 200 and r.json()["title"] == "最终决战"
    r = client.get(f"/api/novels/{novel_id}/events/nope")
    assert r.status_code == 404
test("GET event single + 404", test_event_get_and_404)

def test_snapshot_get_and_404():
    r = client.get(f"/api/novels/{novel_id}/snapshots/snap-1")
    assert r.status_code == 200 and r.json()["name"] == "Carol"
    r = client.get(f"/api/novels/{novel_id}/snapshots/nope")
    assert r.status_code == 404
test("GET snapshot single + 404", test_snapshot_get_and_404)

def test_snapshot_update_keeps_master():
    # editing a historical snapshot must NOT alter the master character card
    master_before = next(c for c in client.get(f"/api/novels/{novel_id}/characters").json() if c["id"] == "char-001")
    r = client.put(f"/api/novels/{novel_id}/snapshots/snap-2", json={
        "id": "snap-2", "source_type": "character", "source_id": "char-001",
        "name": "Alice", "label": "濒死",
        "fields": {"current_state": "dying"}, "create_master": False
    })
    assert r.status_code == 200
    snap = client.get(f"/api/novels/{novel_id}/snapshots/snap-2").json()
    assert snap["label"] == "濒死" and snap["fields"]["current_state"] == "dying"
    master_after = next(c for c in client.get(f"/api/novels/{novel_id}/characters").json() if c["id"] == "char-001")
    assert master_after == master_before, "master card must remain unchanged"
test("Update snapshot does not touch master", test_snapshot_update_keeps_master)

def test_multi_canvas_placement():
    r = client.put(f"/api/novels/{novel_id}/canvas/ch-1", json={
        "node_id": "ch-1",
        "nodes": [{"placement_id": "pl-9", "entity_type": "snapshot", "entity_id": "snap-1", "x": 5, "y": 5}],
        "edges": [], "viewport": None
    })
    assert r.status_code == 200
    pls = client.get(f"/api/novels/{novel_id}/snapshots/snap-1/placements").json()
    node_ids = {p["node_id"] for p in pls}
    assert {"vol-1", "ch-1"}.issubset(node_ids), f"got {node_ids}"
    titles = {p["node_title"] for p in pls}
    assert "Chapter 1" in titles and "Vol 1" in titles
test("Snapshot placements across multiple canvases", test_multi_canvas_placement)

def test_canvas_overwrite():
    client.put(f"/api/novels/{novel_id}/canvas/sec-1-1", json={
        "node_id": "sec-1-1",
        "nodes": [
            {"placement_id": "a", "entity_type": "event", "entity_id": "ev-1", "x": 0, "y": 0},
            {"placement_id": "b", "entity_type": "event", "entity_id": "ev-1", "x": 1, "y": 1},
        ],
        "edges": [], "viewport": None
    })
    client.put(f"/api/novels/{novel_id}/canvas/sec-1-1", json={
        "node_id": "sec-1-1",
        "nodes": [{"placement_id": "a", "entity_type": "event", "entity_id": "ev-1", "x": 0, "y": 0}],
        "edges": [], "viewport": None
    })
    data = client.get(f"/api/novels/{novel_id}/canvas/sec-1-1").json()
    assert len(data["nodes"]) == 1
test("Canvas overwrite replaces nodes", test_canvas_overwrite)

def test_event_delete():
    client.post(f"/api/novels/{novel_id}/events", json={"id": "ev-del", "title": "tmp", "description": ""})
    r = client.delete(f"/api/novels/{novel_id}/events/ev-del")
    assert r.status_code == 200
    assert not any(e["id"] == "ev-del" for e in client.get(f"/api/novels/{novel_id}/events").json())
test("DELETE event", test_event_delete)

def test_snapshot_delete():
    client.post(f"/api/novels/{novel_id}/snapshots", json={
        "id": "snap-del", "source_type": "free", "source_id": None,
        "name": "tmp", "label": "", "fields": {}, "create_master": False
    })
    r = client.delete(f"/api/novels/{novel_id}/snapshots/snap-del")
    assert r.status_code == 200
    assert not any(s["id"] == "snap-del" for s in client.get(f"/api/novels/{novel_id}/snapshots").json())
test("DELETE snapshot", test_snapshot_delete)

def test_free_snapshot_no_master():
    before = len(client.get(f"/api/novels/{novel_id}/characters").json())
    bw = len(client.get(f"/api/novels/{novel_id}/world").json())
    client.post(f"/api/novels/{novel_id}/snapshots", json={
        "id": "snap-free", "source_type": "free", "source_id": None,
        "name": "随手便签", "label": "", "fields": {"personality": "note"}, "create_master": True
    })
    assert len(client.get(f"/api/novels/{novel_id}/characters").json()) == before
    assert len(client.get(f"/api/novels/{novel_id}/world").json()) == bw
test("Free snapshot never creates master", test_free_snapshot_no_master)

def test_setting_snapshot_sync_master():
    bw = len(client.get(f"/api/novels/{novel_id}/world").json())
    client.post(f"/api/novels/{novel_id}/snapshots", json={
        "id": "snap-ws", "source_type": "setting", "source_id": None,
        "name": "新设定", "label": "", "fields": {"category": "place", "description": "d"},
        "create_master": True
    })
    ws = client.get(f"/api/novels/{novel_id}/world").json()
    assert len(ws) == bw + 1 and any(w["name"] == "新设定" for w in ws)
test("Setting snapshot syncs world master", test_setting_snapshot_sync_master)

def test_snapshot_category_roundtrip():
    r = client.post(f"/api/novels/{novel_id}/snapshots", json={
        "id": "snap-cat", "source_type": "free", "source_id": None,
        "name": "阵营便签", "label": "", "category": "主角阵营",
        "fields": {"personality": "x"}, "create_master": False
    })
    assert r.status_code == 200
    s = client.get(f"/api/novels/{novel_id}/snapshots/snap-cat").json()
    assert s["category"] == "主角阵营"
    r = client.put(f"/api/novels/{novel_id}/snapshots/snap-cat", json={
        "id": "snap-cat", "source_type": "free", "source_id": None,
        "name": "阵营便签", "label": "", "category": "反派阵营",
        "fields": {"personality": "x"}, "create_master": False
    })
    assert r.status_code == 200
    assert client.get(f"/api/novels/{novel_id}/snapshots/snap-cat").json()["category"] == "反派阵营"
test("Snapshot category persists + updatable", test_snapshot_category_roundtrip)

def test_agent_logs():
    from backend import storage as st
    st.save_agent_log(novel_id, "run-test", {
        "run_id": "run-test", "section_id": "sec-1-1", "section_title": "Section 1",
        "instruction": "写正文", "model": "deepseek-chat",
        "started_at": "2026-01-01T00:00:00", "finished_at": "2026-01-01T00:01:00",
        "status": "done",
        "events": [{"step": "init", "status": "running", "message": "构建上下文"},
                   {"step": "tool_call", "status": "done", "tool": "get_outline", "message": "x"}],
        "final_content": "正文内容",
    })
    lst = client.get(f"/api/novels/{novel_id}/agent/logs").json()
    item = next(l for l in lst if l["run_id"] == "run-test")
    assert item["event_count"] == 2 and item["final_len"] == 4 and item["status"] == "done"
    full = client.get(f"/api/novels/{novel_id}/agent/logs/run-test").json()
    assert full["final_content"] == "正文内容" and len(full["events"]) == 2
    assert client.get(f"/api/novels/{novel_id}/agent/logs/nope").status_code == 404
    assert client.delete(f"/api/novels/{novel_id}/agent/logs/run-test").status_code == 200
    assert not any(l["run_id"] == "run-test" for l in client.get(f"/api/novels/{novel_id}/agent/logs").json())
test("Agent logs persist + query + delete", test_agent_logs)

def test_pipeline_context():
    from backend.app.pipeline import gather_plan_context, coerce_plan, coerce_review
    ctx = gather_plan_context(novel_id, "sec-1-1")
    assert ctx["section"]["title"] == "Section 1"
    assert "Alice" in ctx["char_names"]
    assert "Magic System" in ctx["setting_names"]
    # coerce_plan 只保留可用名
    plan = coerce_plan({"involved_characters": ["Alice", "不存在"], "involved_settings": ["Magic System"],
                        "this_goal": "目标", "beats": "b1\nb2"}, ctx)
    assert plan["involved_characters"] == ["Alice"]
    assert plan["involved_settings"] == ["Magic System"]
    assert plan["beats"] == ["b1", "b2"]
    rv = coerce_review({"ok": False, "issues": [{"type": "对话", "severity": "minor", "description": "x"}]})
    assert rv["ok"] is False and len(rv["issues"]) == 1 and rv["issues"][0]["type"] == "对话"
test("Pipeline context gather + coerce", test_pipeline_context)

def test_pipeline_graph_flow():
    import asyncio, json as _json
    from langgraph.checkpoint.memory import MemorySaver
    from backend.app.pipeline import build_graph

    class _Resp:
        def __init__(self, c): self.content = c
    class _FakeLLM:
        async def ainvoke(self, m):
            s = m[0]["content"]
            if "策划" in s:
                return _Resp(_json.dumps({"involved_characters": ["Alice"], "involved_settings": ["Magic System"],
                                          "prev_recap": "p", "this_goal": "g", "next_setup": "n", "beats": ["b1", "b2"]}))
            if "审稿" in s:
                return _Resp(_json.dumps({"ok": False, "issues": [{"type": "对话", "severity": "minor", "description": "平", "suggestion": "改"}]}))
            if "改写" in s or "修订" in s: return _Resp("修订正文。" * 6)
            if "编辑" in s: return _Resp("润色终稿。" * 6)
            return _Resp("草稿正文。" * 6)

    async def run():
        g = build_graph(_FakeLLM(), MemorySaver())
        cfg = {"configurable": {"thread_id": "t-test"}, "recursion_limit": 50}
        init = {"novel_id": novel_id, "section_id": "sec-1-1", "style_id": None, "instruction": "写", "run_id": "t-test"}
        async for _ in g.astream(init, config=cfg, stream_mode="updates"):
            pass
        st = await g.aget_state(cfg)
        assert st.next == ("write",), f"应在 plan 后暂停, next={st.next}"
        assert st.values.get("plan", {}).get("involved_characters") == ["Alice"]
        # 确认计划（编辑）
        await g.aupdate_state(cfg, {"plan": {**st.values["plan"], "this_goal": "edited"}})
        async for _ in g.astream(None, config=cfg, stream_mode="updates"):
            pass
        st = await g.aget_state(cfg)
        assert st.next, "应在 review 后暂停"
        assert len(st.values.get("draft", "")) > 0
        assert st.values["plan"]["this_goal"] == "edited"
        # 选择修订一次（循环）
        await g.aupdate_state(cfg, {"action": "revise"})
        async for _ in g.astream(None, config=cfg, stream_mode="updates"):
            pass
        st = await g.aget_state(cfg)
        assert st.next, "修订后应再次在 review 暂停"
        # 润色 → 完成
        await g.aupdate_state(cfg, {"action": "polish"})
        async for _ in g.astream(None, config=cfg, stream_mode="updates"):
            pass
        st = await g.aget_state(cfg)
        assert st.next == (), f"应完成, next={st.next}"
        assert len(st.values.get("final", "")) > 0
    asyncio.run(run())
test("Pipeline graph: plan→write→review→revise→polish (stub LLM)", test_pipeline_graph_flow)

# ─── 13. Cleanup ───
print("\n--- 13. Cleanup ---")
def test_delete_novel():
    r = client.delete(f"/api/novels/{novel_id}")
    assert r.status_code == 204
    r2 = client.get(f"/api/novels/{novel_id}")
    assert r2.status_code == 404
test("DELETE novel + verify 404", test_delete_novel)

print("\n" + "=" * 50)
print(f" Results: {PASS} passed, {FAIL} failed")
print("=" * 50)
sys.exit(1 if FAIL > 0 else 0)
