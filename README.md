# NovelAgent

基于 **LangChain** + **LangGraph** 的 AI 长篇小说写作辅助工具。

大纲驱动，用户设计结构 → Agent 通过 ReAct 循环自动创作/润色/审查。

## 架构

```
NovelAgent/
├── backend/
│   ├── main.py            # FastAPI 入口
│   ├── storage.py         # JSON 文件持久化
│   ├── app/
│   │   ├── agent.py       # LangGraph ReAct Agent
│   │   ├── tools.py       # 6 个 LangChain Tool
│   │   ├── memory.py      # ChromaDB RAG（向量检索）
│   │   ├── prompts.py     # Agent 系统提示词
│   │   └── skills/        # 8 个 Prompt 模板(.md)
│   └── routers/           # REST API 路由
├── frontend/
│   └── src/
│       ├── pages/         # 7 个页面
│       ├── api/           # API 客户端（含 SSE 消费）
│       └── store/         # Zustand 状态管理
├── start.bat              # Windows 一键启动
└── test_all.py            # 测试套件（28 项）
```

## 功能

- **项目管理** — 创建/删除小说项目
- **大纲编辑** — 卷→章→节 三级树形结构，支持节点插入/删除/编辑/内联摘要
- **LangChain Agent** — 自然语言指令驱动，ReAct 循环自动获取上下文→创作→完成
- **RAG 记忆** — ChromaDB + sentence-transformers 向量检索，Agent 自动搜索前文
- **生成摘要** — LLM 归纳正文为结构化 JSON，自动标记完成并写入上下文链
- **角色卡片** — 名称/定位/外貌/性格/背景/能力/说话风格/弧光/关系
- **世界观设定** — 7 类分类筛选（环境/势力/规则/种族/物品/职业/历史）
- **模型设置** — API Key Base64 编码存 localStorage，支持任意 OpenAI 兼容 API
- **深色模式** — 手动切换，全局 CSS 变量

## Agent 工具

| 工具 | 用途 |
|------|------|
| `get_outline` | 读取完整大纲结构（卷→章→节） |
| `get_characters` | 读取角色档案 |
| `get_world_settings` | 读取世界观设定 |
| `get_summaries` | 读取前文摘要 |
| `search_memory` | ChromaDB RAG 向量检索已写内容 |
| `finish` | 完成任务，返回创作的正文 |

Agent 流程：获取数据 → LLM 推理 → 创作正文 → `finish` 返回结果，全部通过 SSE 流式推送到前端。

## 快速开始

### 环境要求
- Python 3.9+
- Node.js 18+

### 安装

```bash
pip install -r backend/requirements.txt
cd frontend && npm install
```

### 启动

**Windows：** 双击 `start.bat`

**手动：**
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
cd frontend && npm run dev
```

浏览器访问 http://localhost:3001

### 配置 LLM
1. 进入项目 → 侧边栏「模型设置」
2. 填入 API Key（DeepSeek / OpenAI 等）
3. 可自定义 model、base_url、temperature、max_tokens

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/novels` | 项目列表 |
| POST | `/api/novels` | 创建项目 |
| DELETE | `/api/novels/:id` | 删除项目 |
| GET | `/api/novels/:id/outline` | 获取大纲 |
| PUT | `/api/novels/:id/outline` | 保存大纲 |
| GET | `/api/novels/:id/outline/section/:sid/content` | 获取正文 |
| PUT | `/api/novels/:id/outline/section/:sid/content` | 保存正文 |
| GET | `/api/novels/:id/characters` | 角色列表 |
| PUT | `/api/novels/:id/characters` | 保存角色 |
| GET | `/api/novels/:id/world` | 世界观列表 |
| PUT | `/api/novels/:id/world` | 保存世界观 |
| POST | `/api/novels/:id/agent/run` | 运行 LangChain Agent（SSE 流式） |
| POST | `/api/novels/:id/agent/summrize` | 生成摘要 |

## 数据存储

```
backend/data/{novel_id}/
├── meta.json           # 项目元信息
├── outline.json        # 大纲树（卷→章→节）
├── characters.json     # 角色卡片
├── world_settings.json # 世界观设定
├── summaries.json      # 已完成章节摘要
└── sections/           # 各节正文 .txt
```

RAG 向量存储在 `backend/data/chroma/`（ChromaDB 持久化目录）。

## 测试

```bash
python test_all.py
```
