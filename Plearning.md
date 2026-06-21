# NovelAgent — 项目面试学习指南

> 零经验候选人备战大厂实习，逐行理解代码 + 技术扩展 + HR 问答 + 完整链路口述

---

## 一、完整目录递归

```
NovelAgent/
├── ═══════════════ 入口 / 文档 ═══════════════
├── README.md                     # 项目说明（架构图、API、快速开始）
├── test_all.py                   # 测试套件（FastAPI TestClient, 24项）
├── start.bat                     # Windows 一键启动
│
├── ═══════════════ Agent/ (核心业务层) ═══════════════
│   └── makenovel_agent/
│       ├── ⚡ llm.py             # LLM 通信层（OpenAI SDK封装 + JSON容错）
│       ├── ⚡ pipeline.py        # 管道编排器（5Agent串联 + 两轮熔断）
│       ├── agents/
│       │   ├── preparer.py      # 准备者：大纲分析 + 筛选角色/世界观
│       │   ├── creator.py       # 创作者：生成正文初稿
│       │   ├── reviewer.py      # 审查者：6维度逻辑检查
│       │   ├── reviser.py       # 修订者：最小改动修Bug
│       │   └── polisher.py      # 润色者：文笔优化不动情节
│       ├── models/
│       │   ├── outline.py       # OutlineNode(递归树) + OutlineTree
│       │   ├── character.py     # CharacterCard + 角色关系
│       │   ├── world.py         # WorldSetting(7分类)
│       │   ├── summary.py       # SectionSummary + LLM上下文格式化
│       │   └── messages.py      # ⚡ Agent间协议(PreparationResult/ReviewIssue/ReviewResult)
│       └── skills/              # Prompt模板（Markdown文件）
│           ├── preparer.md / writer.md / reviewer.md / reviser.md / polisher.md
│
├── ═══════════════ backend/ (API服务层) ═══════════════
│   ├── main.py                   # FastAPI App + CORS + 路由注册
│   ├── ⚡ storage.py             # JSON文件持久化（零数据库）
│   └── routers/
│       ├── ⚡ agent.py           # Agent端点（SSE流式 + 单步 + 摘要生成）
│       ├── novels.py             # 项目 CRUD
│       ├── outlines.py           # 大纲 + 正文读写
│       ├── characters.py         # 角色 CRUD
│       └── world.py              # 世界观 CRUD
│
├── ═══════════════ frontend/ (展示层) ═══════════════
│   └── src/
│       ├── App.tsx               # 路由配置（React Router v6）
│       ├── api/
│       │   └── ⚡ client.ts      # API客户端（REST + SSE消费）
│       ├── store/
│       │   ├── settings.ts       # ⚡ Zustand: LLM设置(localStorage Base64)
│       │   └── theme.ts          # Zustand: 深色模式
│       └── pages/
│           ├── EditorPage.tsx     # ⚡ 写作页（编辑器+SSE管道进度）
│           ├── OutlinePage.tsx    # 大纲编辑（树形操作）
│           ├── HomePage.tsx       # 首页项目列表
│           ├── NovelLayout.tsx    # 项目布局（侧边栏+Outlet子路由）
│           ├── CharactersPage.tsx # 角色卡片管理
│           ├── WorldPage.tsx      # 世界观管理
│           └── SettingsPage.tsx   # LLM模型配置
└── .gitignore
```

---

## 二、核心模块逐行注释

### 2.1 `llm.py` — LLM 通信层

```python
# 文件: Agent/makenovel_agent/llm.py
# 职责: 所有LLM调用都经过此文件，封装OpenAI SDK，支持多Provider切换

from openai import OpenAI

# ===== 配置：dataclass定义 =====
@dataclass
class LLMConfig:
    # 为什么用field(default_factory=lambda: os.getenv(...))?
    # → 确保每次创建对象时重新读环境变量，而非类加载时固化
    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    base_url: str = "https://api.deepseek.com"       # 可替换为任意OpenAI兼容API
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096

# ===== 客户端：适配器模式 =====
class LLMClient:
    def __init__(self, config=None):
        self.config = config or LLMConfig()
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,      # ← 关键：通过base_url切换Provider
        )

    # ── chat(): 返回原始文本 ──
    def chat(self, system_prompt, user_message, temperature=None, max_tokens=None):
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},  # skills/*.md的内容
                {"role": "user", "content": user_message},      # 动态上下文
            ],
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
        )
        return response.choices[0].message.content or ""

    # ── chat_json(): 返回dict ──
    def chat_json(self, system_prompt, user_message, temperature=0.3):
        text = self.chat(...)
        return self._parse_json(text)

    # ── ⚡ 三级降级JSON解析（LLM应用的核心容错） ──
    def _parse_json(self, text):
        text = text.strip()
        # 第1层：去掉 ```json ... ``` markdown代码块
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].strip() == "```": lines = lines[:-1]
            text = "\n".join(lines)
        # 第2层：直接json.loads
        try: return json.loads(text)
        except: pass
        # 第3层：暴力截取 { ... }
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try: return json.loads(text[start:end+1])
            except: pass
        raise ValueError(f"无法解析JSON: {text[:500]}")
```

**技术扩展 — LLM JSON可靠性方案：**

| 方案 | 成功率 | 本项目？ |
|------|--------|---------|
| prompt约束 + 解析容错 | ~85% | ✅ 本项目 |
| OpenAI JSON Mode | ~95% | 未用（需API支持） |
| 二次自我修复（让LLM修自己的JSON） | ~90% | NS项目用到 |
| 正则+文法修复 | 不推荐 | 复杂度太高 |

---

### 2.2 `pipeline.py` — 管道编排器

```python
# 文件: Agent/makenovel_agent/pipeline.py
# 职责: 串联5个Agent，控制执行顺序，实现两轮审查熔断

@dataclass
class PipelineResult:
    section_id: str
    preparation: PreparationResult      # Pydantic模型（有6个子字段）
    draft_content: str                  # 纯字符串（创作者初稿，无需元数据）
    review_result: ReviewResult         # Pydantic模型（用于分流判断）
    revised_content: str
    final_content: str
    logs: list[str]

class NovelAgentPipeline:
    def run(self, section_id, outline_tree, characters,
            world_settings, summaries, content_override=None):

        # ═══ 准备 ═══
        preparation = self.preparer.prepare(
            section_id=section_id,
            outline_tree=outline_tree,          # 完整大纲（卷→章→节）
            summaries=summaries,                # 前文摘要链
            characters=characters,              # 全部角色
            world_settings=world_settings,      # 全部世界观
            llm=self.llm,
        )

        # ═══ 创作 ═══
        draft = self.creator.write(preparation, llm=self.llm,
                                    content=content_override)

        # ═══ 审查 ═══
        review_result = self.reviewer.review(
            content=draft,
            characters=preparation.involved_characters,
            world_settings=preparation.involved_world_settings,
            llm=self.llm,
        )

        # ═══ 修订（含二次审查熔断） ═══
        if review_result.issues:
            revised = self.reviser.revise(draft, review_result, llm=self.llm)
            # ⚡ 关键：has_critical_issues 触发第二轮
            if review_result.has_critical_issues:
                review2 = self.reviewer.review(revised, ...)
                if review2.issues:
                    revised = self.reviser.revise(revised, review2, llm=self.llm)
                review_result = review2
        else:
            revised = draft                     # 无问题则跳过修订

        # ═══ 润色 ═══
        final = self.polisher.polish(revised, llm=self.llm)

        return PipelineResult(final_content=final, ...)
```

**为什么 `draft_content` 用 string 而不是 Pydantic 模型？**

| 阶段产出 | 类型 | 原因 |
|----------|------|------|
| `preparation` | PreparationResult | 6个字段各有不同用途，下游需分别读取 |
| `review_result` | ReviewResult | `has_critical_issues` 用于分流判断 |
| `draft/revision/final` | str | 下游只做"读全文改全文"，无按字段区分的需求 |

---

### 2.3 SSE 推流 — 后端端到端

```python
# 文件: backend/routers/agent.py

# ── SSE事件格式化 ──
def _sse_event(data: dict) -> str:
    # ensure_ascii=False 确保中文不转义为\uXXXX
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

@router.post("/run-stream")
def run_pipeline_stream(novel_id, body):
    # 加载上下文数据
    outline = storage.get_outline(novel_id)
    characters = storage.get_characters(novel_id)
    world = storage.get_world_settings(novel_id)
    summaries = storage.get_summaries(novel_id)

    # 构建LLM客户端
    config = LLMConfig(api_key=body.api_key, base_url=body.base_url,
                        model=body.model, ...)
    llm = LLMClient(config)

    # ⚡ Generator：每完成一步就yield一个事件
    def generate():
        try:
            # 准备者
            yield _sse_event({"step": "preparer", "status": "running"})
            preparation = PreparerAgent(skills_dir).prepare(...)
            yield _sse_event({"step": "preparer", "status": "done",
                              "detail": {...}})

            # 创作者
            yield _sse_event({"step": "creator", "status": "running"})
            draft = CreatorAgent(skills_dir).write(preparation, llm=llm)
            yield _sse_event({"step": "creator", "status": "done",
                              "detail": {"content": draft}})

            # 审查者 ...
            # 修订者 ...
            # 润色者 ...

            storage.save_section_content(novel_id, section_id, final)
            yield _sse_event({"step": "complete", "final_content": final})

        except Exception as e:
            # 异常也不断连接，返回error事件
            yield _sse_event({"step": "error", "message": str(e)})

    # ⚡ StreamingResponse + Generator = SSE长连接
    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

### 2.4 前端 SSE 消费

```typescript
// 文件: frontend/src/api/client.ts

runStream: async (params, onEvent) => {
    const res = await fetch(`${BASE}/novels/${id}/agent/run-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
    });

    const reader = res.body!.getReader();   // ⚡ 获取流读取器
    const decoder = new TextDecoder();      // 字节→文本
    let buffer = "";                        // 行缓冲区

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";         // 不完整行保留到下次

        for (const line of lines) {
            if (line.startsWith("data: ")) {
                const data = JSON.parse(line.slice(6));  // 去掉"data: "
                onEvent(data);                           // 回调React更新UI
            }
        }
    }
}
```

**SSE 前后端配合关系：**

```
后端: Generator → yield "块1" ────网络────→ reader.read() → "块1"  前端
       Generator → yield "块2" ────网络────→ reader.read() → "块2"
       Generator → yield "块3" ────网络────→ reader.read() → "块3"
       Generator → return     ────网络────→ done=true 断开
```

**为什么要 buffer？** TCP 是流协议，一次 `read()` 可能拿到半个 SSE 事件。buffer 存放不完整行，等下次数据到达时拼齐再处理。

**为什么不用 EventSource？** EventSource 只支持 GET，本项目需要 POST 传 body（API Key 等参数）。

---

### 2.5 `messages.py` — Agent 间通信协议

```python
# 准备者 → 创作者
class PreparationResult(BaseModel):
    starting_state: str       # 起始状态（故事从哪开始）
    what_to_write: str        # 要写什么（本节目标）
    ending_state: str         # 终止状态（写完应该到哪）
    involved_characters: list[CharacterCard]
    involved_world_settings: list[WorldSetting]
    context_summaries: list[SectionSummary]

    def format_for_writer(self) -> str:   # 结构化→LLM prompt
        """将6个字段组装成创作者可读的文本上下文"""
        ...

# 审查者 → 修订者
class ReviewIssue(BaseModel):
    issue_type: Literal["logic","character_consistency","world_setting",
                         "plot_hole","pacing","dialogue"]  # 6种类型
    severity: Literal["critical","major","minor"]          # 3级严重度
    description: str
    suggestion: str

class ReviewResult(BaseModel):
    issues: list[ReviewIssue]
    has_critical_issues: bool     # ⚡ pipeline用它做分流判断
```

---

### 2.6 `storage.py` — 数据持久化

```python
DATA_DIR = Path(__file__).parent / "data"

def get_outline(novel_id):     # 读大纲（只有结构）
    f = DATA_DIR / novel_id / "outline.json"
    return json.loads(f.read_text(encoding="utf-8"))

def save_section_content(novel_id, section_id, content):
    f = DATA_DIR / novel_id / "sections" / f"{section_id}.txt"
    f.write_text(content, encoding="utf-8")  # 正文独立文件
```

**为什么正文不放在 `outline.json` 里？**

1. **读的粒度**：大纲页只读结构（2KB），不需要加载全书正文（400KB）
2. **写的粒度**：自动保存每秒触发，改一个字只写当前节（2KB），不是重写全书
3. **并发安全**：将来两个 Agent 同时写不同节，独立文件不会互相覆盖

---

### 2.7 5 个 Agent 模式对比

所有 Agent 遵循同一模式：

```python
class XxxAgent:
    # ① 加载skill markdown → self.prompt_template
    def __init__(self, skills_dir):
        self.prompt_template = (skills_dir / "xxx.md").read_text()

    # ② 构建完整prompt
    def build_prompt(self, ...):
        return f"{self.prompt_template}\n\n---\n\n{context}"

    # ③ 执行（三态：override / LLM / 占位）
    def execute(self, ..., llm=None, content=None):
        if content is not None: return content
        if llm: return self._execute_with_llm(...)
        return self._generate_placeholder(...)   # 调试用
```

**各 Agent 的 temperature：**

| Agent | temperature | 理由 |
|-------|-------------|------|
| 准备者 | 0.3 | 确定性的结构化分析 |
| 创作者 | 0.8 | 创作需要多样性 |
| 审查者 | 0.3 | 审查要求一致性 |
| 修订者 | 0.6 | 灵活但不离谱 |
| 润色者 | 0.5 | 平衡可读性与忠实性 |
| 摘要 | 0.3 | 结构化输出 |

---

### 2.8 前端状态管理

```typescript
// 文件: frontend/src/store/settings.ts

// Zustand一行创建store（vs Redux需action/reducer/connect）
export const useSettingsStore = create<SettingsState>((set, get) => ({
    settings: { ...DEFAULT_SETTINGS },

    save: (partial) => {
        // ⚡ 展开运算符合并：只改temperature不需要传完整settings
        const next = { ...get().settings, ...partial };
        set({ settings: next });
        localStorage.setItem(STORAGE_KEY, encodeSettings(next));
        // encodeSettings = btoa(encodeURIComponent(JSON.stringify(s)))
        // → Base64编码（仅防肩窥，不是加密）
    },
}));

// 深色模式
function applyTheme(dark: boolean) {
    // 只切换body上的一个class，CSS变量自动生效
    document.body.classList.toggle("dark", dark);
}
```

---

### 2.9 `OutlineNode` 递归树设计

```python
class OutlineNode(BaseModel):
    id: str
    title: str
    node_type: Literal["volume", "chapter", "section"]
    children: list[OutlineNode]      # ⚡ 自引用递归类型
    sort_order: float = 0.0          # ⚡ 浮点数排序

    def find_node(self, node_id):    # 递归查找
        if self.id == node_id: return self
        for child in self.children:
            r = child.find_node(node_id)
            if r: return r
        return None
```

**`sort_order` 为什么用浮点数？** 插入节点到 A(1.0) 和 B(2.0) 之间，只需 `1.5`。用整数则需重排后面所有节点。

---

## 三、技术扩展

### 3.1 FastAPI

| 知识点 | 本项目体现 | 扩展 |
|--------|-----------|------|
| 异步支持 | 未显式使用async（文件I/O是同步的） | `run_in_threadpool`自动处理 |
| OpenAPI | 自动生成（访问`:8001/docs`） | Pydantic模型自动转为schema |
| StreamingResponse | SSE推流 | 对比WebSocket（双向/无需POST传参） |
| CORS中间件 | `allow_origins=["*"]` | 生产需限定域名 |

### 3.2 Pydantic v2

| v1 API | v2 API | 本项目使用 |
|--------|--------|-----------|
| `.dict()` | `.model_dump()` | ✅ |
| `.json()` | `.model_dump_json()` | 未用到 |
| `.parse_obj(d)` | `.model_validate(d)` | 未用到 |
| 性能 | Rust pydantic-core (5-50x) | 受益于v2 |

### 3.3 Zustand vs Redux vs Jotai

| 维度 | Zustand | Redux Toolkit | Jotai |
|------|---------|--------------|-------|
| 样板代码 | 极少 | 中等(slice) | 极少 |
| Provider包裹 | 不需要 | 需要 | 需要 |
| 规模适用 | 中小型 | 大型 | 细粒度 |
| 本项目选择理由 | 2个store够用 | 过度工程 | 不需要原子化 |

### 3.4 SSE vs WebSocket vs 轮询

| 维度 | SSE | WebSocket | 轮询 |
|------|-----|-----------|------|
| 方向 | 单向(服→客) | 双向 | 客→服 |
| 协议 | HTTP | TCP升级 | 多次HTTP |
| 自动重连 | 内置 | 需手动 | 每次重建 |
| 本项目选择理由 | 只需服务端推送，不需客户端回发 | | |

---

## 四、HR 面试高概率题

### 4.1 关于 AI 辅助编程

**Q：这个项目你独立完成的吗？用了 AI 工具吗？**

推荐回答：

> "架构设计是我独立完成的——多Agent管道的拆分方案、SSE推送的选型、大纲树的递归结构。具体实现中我用了AI编程助手加速，但生成的代码我都逐行理解并验证过。比如 `_parse_json()` 的容错逻辑——初版只有 `json.loads`，我在测试中发现LLM经常在JSON外加markdown代码块，于是自己加了二层剥代码块、三层截花括号。
>
> 我认为AI是好的编码加速器，但架构决策和底层理解必须自己把关。"

### 4.2 关于零工作经验

**Q：你没有实习经验，凭什么觉得自己能胜任？**

> "这个项目是完整的前后端开发——从架构设计、技术选型、编码实现、测试编写到部署脚本，该做的都做了。后端要处理的API设计、异常处理、第三方服务对接，我在这个项目里全碰到了。我缺的是团队协作和code review经验，但我证明了自己有独立把一个想法做到可运行产品的自驱力。"

### 4.3 关于项目理解

**Q：为什么用5个Agent而不是1次LLM调用？**

> "单一职责。拆开后每个Agent只有一件事要做，prompt简洁聚焦，LLM不容易角色混淆。中间审查者的输出（发现了哪些问题）可以作为可观测的中间结果展示给用户。出了问题可以针对性重试某一步，不用从头跑。这是对LLM输出不稳定性的防御性设计。"

### 4.4 行为题

**Q：项目遇到的最大Bug是什么？**

> "LLM的JSON格式不稳定。`json.loads`直接解析成功率只有70%，要么被markdown代码块包裹，要么前后有废话文字。我分析了失败样本后实现了三层降级：直接解析→剥代码块→截花括号块，最终覆盖率到95%+。"

---

## 五、快速自测清单

不看代码能立刻回答吗？

- [ ] 5个Agent的称呼和执行顺序？
- [ ] `PreparationResult` 的3个核心字段？(`starting_state/what_to_write/ending_state`)
- [ ] `_parse_json()` 做了哪三层降级？
- [ ] SSE后端用 `StreamingResponse`，前端用 `getReader()`——为什么这样配合？
- [ ] 正文为什么存 `.txt` 而非嵌在 `outline.json`？
- [ ] `sort_order` 为什么用浮点数？
- [ ] 审查者发现 `critical` 问题会触发什么？最多几轮？
- [ ] 为什么不传 `llm` 给准备者也能工作？
- [ ] `LLMConfig` 用 `dataclass`，API请求体用 `BaseModel`——为什么不一样？
- [ ] 前端发 SSE 为什么不用 `EventSource`？
- [ ] `NovelLayout` 侧边栏和内容区怎么联动的？(`<Outlet />`)
- [ ] Zustand 的 `save(partial)` 为什么用展开运算符合并？

---

## 六、完整链路闭眼口述（面试实战 3 分钟版）

> 面试官：「你在项目中写的 Agent 管道，从用户操作到最终结果全过程是怎么跑的？」

用户点击 `EditorPage` 侧边栏的「完整管道」按钮，`runPipelineStream()` 函数首先从 Zustand store 里取 LLM 配置。如果 API Key 为空，弹框提醒用户配置。确认有 Key 后，先把编辑器中的正文通过防抖 timer 自动保存到后端，保证内容不丢失。

然后调用 `api.agent.runStream()`，用 fetch 发起 POST 到 `/api/novels/{id}/agent/run-stream`。请求 body 包含当前节 ID 和 LLM 参数。用 `getReader()` 获取 `ReadableStream` 的读取器，进入 `while(true)` 循环，每次 `read()` 拿到一块字节，buffer 按行分割，匹配 `data:` 前缀的行，JSON.parse 后回调 `onEvent` 更新 React 状态。

请求到达 FastAPI 后端后，`agent.py` 的 `run_pipeline_stream` 路由接收。Pydantic 自动校验请求体，然后从 `storage.py` 加载 4 份数据——大纲树、角色卡片、世界观设定、前文摘要。构建 `LLMClient`，传入用户配置的 api_key、base_url、model。

然后创建一个 Generator 函数，用 `StreamingResponse` 包起来返回。Generator 内部执行 5 个 Agent 依次执行。

**第一步**，准备者发 running 事件，在完整大纲树中找到当前节，拼接上下文——前文 5 章摘要、全部角色卡片、全部世界观设定——用 `chat_json` 请求 LLM 返回结构化 JSON。解析后得到三段式情节分析：`starting_state`、`what_to_write`、`ending_state`，以及相关的角色和世界观列表。完成后发 done 事件。

**第二步**，创作者发 running，接收 PreparationResult，调用 `format_for_writer()` 转成 LLM prompt。用 `temperature=0.8` 保证创造性。如果当前节已有正文，作为 content 参数传入，创作者在此基础上续写而非重写。

**第三步**，审查者接收初稿和被筛选的角色/世界观，从 6 个维度检查——逻辑一致性、角色一致性、世界观一致性、情节漏洞、节奏、对话。返回 `ReviewResult`，含 issues 列表和 `has_critical_issues` 字段。

**第四步**，修订者根据问题做最小改动。如果 `has_critical_issues` 为 True，修订后启动第二轮审查-修订——审查者检查修改后的内容，再有问题修订者再修一次。最多两轮，这是熔断机制防止 LLM 无限修改。如果没问题直接跳过修订。

**第五步**，润色者只优化文笔，不动情节。

最后，最终正文写入 `sections/{id}.txt`，yield complete 事件带 final_content。前端收到后自动把正文填入编辑器 textarea。

整个管道耗时 1-2 分钟，用户通过 SSE 实时看到每一步进展和中间结果，体验是渐进式的而非黑盒等待。

---

## 七、面试追问速查

| 如果被问 | 这样答 |
|---------|-------|
| LLM返回不当时怎么处理 | `_parse_json`三级降级 + 不同Agent用不同temperature |
| 性能瓶颈 | 5次LLM调用累计1-2分钟，瓶颈在API延迟不在本地 |
| 为什么JSON文件不用数据库 | 单用户工具无并发需求，大纲树天然JSON，零运维 |
| 如果用户量到1万 | 切换SQLite/PostgreSQL，API Key存服务端，加认证 |
| 怎么保证管道不丢数据 | Pydantic字段类型编译时确定，LLM缺字段有默认值兜底 |
| Agent间解耦怎么做 | 通过Pydantic模型定义契约，每个Agent只知道自己需要什么 |
