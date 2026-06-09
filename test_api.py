"""MakeNovel API test suite"""
import json
import urllib.request
import urllib.error
import sys

BASE = "http://127.0.0.1:8000/api"

def req(method, path, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r) as resp:
            content = resp.read().decode()
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode()
        return e.code, json.loads(content) if content else {"error": str(e)}

def ok(cond, msg):
    if cond:
        print(f"  PASS: {msg}")
    else:
        print(f"  FAIL: {msg}")
        sys.exit(1)

print("=" * 60)
print("MakeNovel API 功能测试")
print("=" * 60)

# 1. Health
print("\n[1] 健康检查")
code, data = req("GET", "/health")
ok(code == 200 and data.get("status") == "ok", f"/api/health -> {data}")

# 2. Novels CRUD
print("\n[2] 小说 CRUD")
code, novel = req("POST", "/novels", {
    "title": "星辰之海",
    "description": "一个关于星际探险的故事",
    "genre": "科幻",
    "style_notes": "第一人称，细腻描写"
})
ok(code == 200, f"创建小说 -> {novel.get('title')} (id={novel.get('id')})")
novel_id = novel["id"]

code, novels = req("GET", "/novels")
ok(code == 200 and len(novels) == 1, f"列出小说 -> {len(novels)} 部")

code, single = req("GET", f"/novels/{novel_id}")
ok(code == 200 and single["title"] == "星辰之海", f"获取小说 -> {single['title']}")

code, updated = req("PUT", f"/novels/{novel_id}", {"title": "星辰之海 (修订版)", "word_count_goal": 100000})
ok(code == 200 and updated["title"] == "星辰之海 (修订版)" and updated["word_count_goal"] == 100000,
   f"更新小说 -> {updated['title']}")

# 3. Chapters CRUD
print("\n[3] 章节 CRUD")
code, chap1 = req("POST", "/chapters", {
    "novel_id": novel_id, "title": "第一章：启航", "chapter_number": 1
})
ok(code == 200, f"创建章节 -> {chap1.get('title')} (id={chap1.get('id')})")
ch1_id = chap1["id"]

code, chap2 = req("POST", "/chapters", {
    "novel_id": novel_id, "title": "第二章：黑暗虚空", "chapter_number": 2
})
ok(code == 200, f"创建章节2 -> {chap2.get('title')} (id={chap2.get('id')})")
ch2_id = chap2["id"]

code, chapters = req("GET", f"/chapters/novel/{novel_id}")
ok(code == 200 and len(chapters) == 2, f"列出章节 -> {len(chapters)} 章")

content = "<p>飞船缓缓驶离港口。星光照亮了舰桥的每一寸角落。</p>"
code, updated_ch = req("PUT", f"/chapters/{ch1_id}", {
    "content": content, "status": "revising"
})
ok(code == 200 and updated_ch["word_count"] > 0 and updated_ch["status"] == "revising",
   f"更新章节 -> 字数={updated_ch['word_count']}, 摘要={updated_ch['summary'][:50] if updated_ch['summary'] else 'N/A'}")

# 4. Characters CRUD
print("\n[4] 角色 CRUD")
code, char1 = req("POST", "/characters", {
    "novel_id": novel_id,
    "name": "李明远",
    "role": "protagonist",
    "profile": {"age": "28", "personality": "冷静沉着", "background": "前军队飞行员"},
    "arc": "从迷茫到找到人生意义"
})
ok(code == 200, f"创建角色 -> {char1.get('name')} (id={char1.get('id')})")
c1_id = char1["id"]

code, char2 = req("POST", "/characters", {
    "novel_id": novel_id,
    "name": "赵星云",
    "role": "supporting",
    "profile": {"age": "25", "personality": "活泼开朗", "speech_style": "快言快语"},
})
ok(code == 200, f"创建角色2 -> {char2.get('name')} (id={char2.get('id')})")
c2_id = char2["id"]

code, chars = req("GET", f"/characters/novel/{novel_id}")
ok(code == 200 and len(chars) == 2, f"列出角色 -> {len(chars)} 个")

code, updated_char = req("PUT", f"/characters/{c1_id}", {"profile": {"age": "29", "personality": "更加沉稳"}})
ok(code == 200, f"更新角色 -> OK")

# 5. Character Relationships
print("\n[5] 角色关系")
code, rel = req("POST", "/characters/relationships", {
    "source_id": c1_id, "target_id": c2_id,
    "relation_type": "朋友/战友", "description": "形影不离的搭档"
})
ok(code == 200, f"创建关系 -> {rel.get('relation_type')}")

code, chars_with_rel = req("GET", f"/characters/novel/{novel_id}")
c1_with_rel = [c for c in chars_with_rel if c["id"] == c1_id][0]
ok(len(c1_with_rel.get("relationships", [])) == 1,
   f"角色关系数 -> {len(c1_with_rel.get('relationships', []))}")

# 6. Settings (World-building) - test all categories
print("\n[6] 场景/世界观 CRUD")
categories = [
    ("location", "星联号飞船", "社会环境", "一艘中型星际探险飞船"),
    ("faction", "银河联邦", "国家", "统辖多个星系的政治实体"),
    ("rule", "曲速跃迁", "", "通过压缩时空实现超光速旅行"),
    ("race", "星际游民", "智慧种族", "在宇宙中流浪的人类分支"),
    ("item", "时空核心", "神器", "驱动曲速引擎的关键能量源"),
    ("profession", "星际探险家", "", "探索未知星域的专业人士"),
    ("history", "第一次接触战争", "战争", "人类与外星文明首次接触引发的冲突"),
]
ids = []
for cat, name, ltype, desc in categories:
    code, s = req("POST", "/settings", {
        "novel_id": novel_id, "name": name, "category": cat,
        "location_type": ltype, "description": desc,
        "notable_features": [f"{name}特征1", f"{name}特征2"]
    })
    ok(code == 200 and s.get("category") == cat,
       f"创建 [{cat}] -> {name} (id={s.get('id')})")
    ids.append(s["id"])

code, settings = req("GET", f"/settings/novel/{novel_id}")
ok(code == 200 and len(settings) == 7, f"列出场景 -> {len(settings)} 个")

code, updated_s = req("PUT", f"/settings/{ids[0]}", {"description": "修改后的飞船描述"})
ok(code == 200 and "修改后" in updated_s["description"], f"更新场景 -> OK")

# 7. Outline CRUD
print("\n[7] 大纲节点 CRUD")
code, vol = req("POST", "/outlines", {
    "novel_id": novel_id, "node_type": "volume", "title": "第一卷：星辰大海",
    "summary": "探索银河系的冒险故事", "sort_order": 0
})
ok(code == 200 and "summary" in vol, f"创建卷 -> {vol.get('title')} (id={vol.get('id')})")
vol_id = vol["id"]

code, section = req("POST", "/outlines", {
    "novel_id": novel_id, "parent_id": vol_id,
    "node_type": "scene", "title": "第一节：出发",
    "summary": "主角决定离开地球", "character_id": c1_id, "setting_id": s1_id, "sort_order": 0
})
ok(code == 200 and section.get("character_id") == c1_id, f"创建节 -> {section.get('title')} (char={section.get('character_id')})")

code, outline = req("GET", f"/outlines/novel/{novel_id}")
ok(code == 200 and len(outline) == 1 and len(outline[0].get("children", [])) == 1,
   f"大纲树 -> {len(outline)} 卷, 子节点={len(outline[0].get('children', []))}")

# 8. AI Actions
print("\n[8] AI 动作列表")
code, actions = req("GET", "/ai/actions")
expected_actions = ["write", "polish", "rewrite", "brainstorm", "summary"]
ok(code == 200 and len(actions) == 5, f"AI 动作数 -> {len(actions)}")
action_names = [a["action"] for a in actions]
for act in expected_actions:
    ok(act in action_names, f"  包含动作: {act}")

# 9. Cleanup - delete test data
print("\n[9] 清理测试数据")
code, _ = req("DELETE", f"/novels/{novel_id}")
ok(code == 200, "删除小说 (级联清理所有数据)")

code, novels = req("GET", "/novels")
ok(code == 200 and len(novels) == 0, f"确认清空 -> {len(novels)} 部小说")

print("\n" + "=" * 60)
print("全部测试通过！")
print("=" * 60)
