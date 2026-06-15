import sys
import json
sys.path.insert(0, "Agent")

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
print(" NovelAgent Test Suite")
print("=" * 50)

novel_id = None

print("\n--- Test 1: Health Check ---")
def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
test("GET /api/health", test_health)

print("\n--- Test 2: Novel CRUD ---")
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
    novels = r.json()
    assert any(n["id"] == novel_id for n in novels)
test("GET /api/novels (list)", test_list_novels)

def test_get_novel():
    r = client.get(f"/api/novels/{novel_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "TestNovel"
test("GET /api/novels/:id (get)", test_get_novel)

print("\n--- Test 3: Outline CRUD ---")
def test_get_outline():
    r = client.get(f"/api/novels/{novel_id}/outline")
    assert r.status_code == 200
    data = r.json()
    assert data["novel_id"] == novel_id
    assert data["volumes"] == []
test("GET outline (empty)", test_get_outline)

def test_save_outline():
    outline = {
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
    r = client.put(f"/api/novels/{novel_id}/outline", json=outline)
    assert r.status_code == 200
test("PUT outline (save tree)", test_save_outline)

def test_get_outline_saved():
    r = client.get(f"/api/novels/{novel_id}/outline")
    assert r.status_code == 200
    data = r.json()
    assert len(data["volumes"]) == 1
    assert data["volumes"][0]["children"][0]["children"][0]["id"] == "sec-1-1"
    assert data["volumes"][0]["children"][0]["children"][0]["summary"] == "Opening scene"
test("GET outline (verify tree)", test_get_outline_saved)

print("\n--- Test 4: Section Content ---")
def test_save_content():
    r = client.put(
        f"/api/novels/{novel_id}/outline/section/sec-1-1/content",
        json={"content": "It was a dark and stormy night..."}
    )
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
test("GET empty section content", test_get_empty_content)

print("\n--- Test 5: Characters CRUD ---")
def test_get_chars_empty():
    r = client.get(f"/api/novels/{novel_id}/characters")
    assert r.status_code == 200
    assert r.json() == []
test("GET characters (empty)", test_get_chars_empty)

def test_add_char():
    char = {
        "id": "char-001",
        "name": "Alice",
        "role": "protagonist",
        "appearance": "tall, dark hair",
        "personality": "brave and kind",
        "background": "orphan from the north",
        "relationships": []
    }
    r = client.post(f"/api/novels/{novel_id}/characters", json=char)
    assert r.status_code == 200
test("POST character (add)", test_add_char)

def test_add_char2():
    char = {
        "id": "char-002",
        "name": "Bob",
        "role": "antagonist",
        "appearance": "short, red eyes",
        "personality": "cunning",
        "background": "dark lord",
        "relationships": [{"source_id": "char-002", "target_id": "char-001", "relation_type": "enemy", "description": "sworn enemy"}]
    }
    r = client.post(f"/api/novels/{novel_id}/characters", json=char)
    assert r.status_code == 200
test("POST character (add 2nd)", test_add_char2)

def test_get_chars():
    r = client.get(f"/api/novels/{novel_id}/characters")
    assert r.status_code == 200
    chars = r.json()
    assert len(chars) == 2
    assert chars[0]["name"] == "Alice"
    assert chars[1]["relationships"][0]["relation_type"] == "enemy"
test("GET characters (verify 2)", test_get_chars)

def test_delete_char():
    r = client.delete(f"/api/novels/{novel_id}/characters/char-002")
    assert r.status_code == 200
    r2 = client.get(f"/api/novels/{novel_id}/characters")
    assert len(r2.json()) == 1
test("DELETE character", test_delete_char)

print("\n--- Test 6: World Settings CRUD ---")
def test_get_world_empty():
    r = client.get(f"/api/novels/{novel_id}/world")
    assert r.status_code == 200
    assert r.json() == []
test("GET world (empty)", test_get_world_empty)

def test_add_world():
    setting = {
        "id": "ws-001",
        "name": "Magic System",
        "category": "rule",
        "description": "Five elements magic",
        "notable_features": ["fire", "water", "earth", "wind", "void"]
    }
    r = client.post(f"/api/novels/{novel_id}/world", json=setting)
    assert r.status_code == 200
test("POST world setting", test_add_world)

def test_add_world2():
    setting = {
        "id": "ws-002",
        "name": "Capital City",
        "category": "location",
        "description": "The grand capital",
        "notable_features": ["huge walls", "floating towers"]
    }
    r = client.post(f"/api/novels/{novel_id}/world", json=setting)
    assert r.status_code == 200
test("POST world setting 2", test_add_world2)

def test_get_world():
    r = client.get(f"/api/novels/{novel_id}/world")
    assert r.status_code == 200
    ws = r.json()
    assert len(ws) == 2
    assert ws[0]["notable_features"] == ["fire", "water", "earth", "wind", "void"]
test("GET world (verify 2)", test_get_world)

def test_delete_world():
    r = client.delete(f"/api/novels/{novel_id}/world/ws-002")
    assert r.status_code == 200
    r2 = client.get(f"/api/novels/{novel_id}/world")
    assert len(r2.json()) == 1
test("DELETE world setting", test_delete_world)

print("\n--- Test 7: Agent Endpoint Validation ---")
def test_agent_no_key():
    r = client.post(f"/api/novels/{novel_id}/agent/run", json={
        "section_id": "sec-1-1",
        "api_key": "",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.7,
        "max_tokens": 4096,
    })
    assert r.status_code == 400, f"expected 400, got {r.status_code}"
test("POST agent/run (empty key => 400)", test_agent_no_key)

def test_agent_single_validation():
    r = client.post(f"/api/novels/{novel_id}/agent/single", json={
        "section_id": "sec-1-1",
        "api_key": "",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.7,
        "max_tokens": 4096,
        "agent_name": "reviewer",
        "content": "Test content"
    })
    assert r.status_code == 400, f"expected 400, got {r.status_code}"
test("POST agent/single (empty key => 400)", test_agent_single_validation)

def test_agent_unknown():
    r = client.post(f"/api/novels/{novel_id}/agent/single", json={
        "section_id": "sec-1-1",
        "api_key": "fake",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.7,
        "max_tokens": 4096,
        "agent_name": "nonexistent",
    })
    assert r.status_code == 400
test("POST agent/single (unknown agent => 400)", test_agent_unknown)

print("\n--- Test 8: Delete Novel (cleanup) ---")
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
