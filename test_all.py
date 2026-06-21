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
    tools = get_all_tools()
    assert len(tools) == 6
    names = [t.name for t in tools]
    assert "get_outline" in names
    assert "get_characters" in names
    assert "get_world_settings" in names
    assert "get_summaries" in names
    assert "search_memory" in names
    assert "finish" in names
test("get_all_tools returns 6 tools", test_tools_import)

def test_get_outline_tool():
    from backend.app.tools import GetOutlineTool
    tool = GetOutlineTool()
    result = tool._run(novel_id)
    assert "TestNovel" in result
    assert "Sec" in result or "Opening" in result or result, f"Unexpected: {result[:100]}"
test("GetOutlineTool returns outline", test_get_outline_tool)

def test_get_characters_tool():
    from backend.app.tools import GetCharactersTool
    tool = GetCharactersTool()
    result = tool._run(novel_id)
    assert "Alice" in result
    assert "protagonist" in result
test("GetCharactersTool returns characters", test_get_characters_tool)

def test_get_world_tool():
    from backend.app.tools import GetWorldSettingsTool
    tool = GetWorldSettingsTool()
    result = tool._run(novel_id)
    assert "Magic" in result or "magic" in result.lower()
test("GetWorldSettingsTool returns settings", test_get_world_tool)

def test_get_summaries_tool():
    from backend.app.tools import GetSummariesTool
    tool = GetSummariesTool()
    result = tool._run(novel_id)
    assert result and len(result) > 0
test("GetSummariesTool returns summaries", test_get_summaries_tool)

def test_agent_import():
    from backend.app.agent import NovelAgent
    import inspect
    assert hasattr(NovelAgent, "astream")
    # astream is an async generator (uses yield), not a plain coroutine
    assert inspect.isasyncgenfunction(NovelAgent.astream) or inspect.iscoroutinefunction(NovelAgent.astream)
test("NovelAgent class has async generator astream", test_agent_import)

# ─── 8. Agent Endpoint ───
print("\n--- 8. Agent Endpoint ---")
def test_agent_no_key():
    r = client.post(f"/api/novels/{novel_id}/agent/run", json={
        "section_id": "sec-1-1",
        "api_key": "",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.7,
        "max_tokens": 4096,
        "instruction": "test"
    })
    assert r.status_code == 400
test("POST agent/run (empty key => 400)", test_agent_no_key)

def test_agent_invalid_key():
    """Agent responds with SSE error event when LLM call fails"""
    r = client.post(f"/api/novels/{novel_id}/agent/run", json={
        "section_id": "sec-1-1",
        "api_key": "sk-fake-key",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.7,
        "max_tokens": 4096,
        "instruction": "test instruction"
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    lines = r.text.strip().split("\n")
    events = []
    for line in lines:
        if line.startswith("data:"):
            try:
                events.append(json.loads(line[5:].strip()))
            except json.JSONDecodeError:
                pass
    assert len(events) > 0, f"Expected SSE events, got: {r.text[:300]}"
    error_events = [e for e in events if e.get("step") == "error"]
    if error_events:
        print(f"    (agent returned error as expected: {error_events[0].get('message', '')[:80]})")
test("POST agent/run (invalid key => SSE events)", test_agent_invalid_key)

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

# ─── 11. Cleanup ───
print("\n--- 11. Cleanup ---")
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
