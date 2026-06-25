# NovelAgent

基于 **LangGraph** 的 AI 长篇小说写作辅助工具。

大纲驱动：用户设计结构 → 写作流水线先**统筹本节计划**（出场角色 / 用到的设定 / 前中后文），经用户确认后**写作 → 审查 → 修订 / 润色**，全程人工可介入。

## 架构

```
NovelAgent/
├── backend/
│   ├── main.py            # FastAPI 入口
│   ├── storage.py         # JSON 文件持久化
│   ├── app/
│   │   ├── pipeline.py    # LangGraph StateGraph 写作流水线
│   │   ├── agent.py       # 流水线 runner（start_plan / resume，SSE）
│   │   ├── tools.py       # RAG 检索工具（接口保留，暂不接线）
│   │   ├── memory.py      # ChromaDB RAG（向量检索）
│   │   ├── prompts.py     # 技能加载器
│   │   └── skills/        # 9 个 Prompt 模板(.md)，含 plan/write/review/rewrite/polish
│   └── routers/           # REST API 路由
├── frontend/
│   └── src/
│       ├── pages/         # 大纲/编辑/角色/世界观/事件/画板/文风/运行日志/模型设置
│       ├── api/           # API 客户端（含 SSE 消费）
│       └── store/         # Zustand 状态管理
├── start.bat              # Windows 一键启动
└── test_all.py            # 测试套件（48 项）
```

## 功能

- **项目管理** — 创建/删除小说项目
- **大纲编辑** — 卷→章→节 三级树形结构，支持节点插入/删除/编辑/内联摘要
- **写作流水线** — Plan→Write→Review→Revise/Polish 多阶段，Plan 与审查后人工可编辑/选择
- **画板** — 每个卷/章/节独立的无限画板：便签（角色/设定的历史快照）+ 事件 + 连线（变化用虚线），支持反查定位
- **角色卡片** — 名称/定位/外貌/性格/背景/能力/说话风格/弧光/关系
- **世界观设定** — 分类筛选（环境/势力/规则/种族/物品/职业/历史）
- **事件** — 小说级全局事件，可在画板复用
- **生成摘要** — LLM 归纳正文为结构化 JSON，自动标记完成并写入上下文链
- **运行日志** — 记录每次流水线运行各阶段的输入/输出，可逐环节核对
- **RAG 记忆** — ChromaDB + sentence-transformers 向量库（`search_memory` 接口已保留，当前流水线暂不接线）
- **模型设置** — API Key Base64 编码存 localStorage，支持任意 OpenAI 兼容 API
- **深色模式** — 手动切换，全局 CSS 变量

## 写作流水线

```
plan ──(暂停·可编辑计划)──▶ write ──▶ review ──(暂停·选择)──┬─▶ revise ─▶ review …（循环）
                                                            └─▶ polish ─▶ save（落盘 + 写入向量库）
```

- **Plan（统筹）**：后端确定性取数（本节 + 前/后节概要 + 全部角色/设定 + 前文摘要）→ LLM 选出本节真正相关的角色与设定，并梳理前文回顾、本节目标、后文铺垫与情节节拍。
- **Write**：仅注入计划选中的角色/设定全文 + 文风 → 创作草稿。
- **Review**：草稿对照计划审查（角色/设定/连贯性），输出问题清单。
- **Revise / Polish**：用户可编辑草稿后选择「继续修订」（循环）或「直接润色」，最终落盘。

技术说明：用 LangGraph `StateGraph` + `AsyncSqliteSaver`（`thread_id` 跨请求持久化）实现。因运行环境为 Python 3.9（`interrupt()` 需 3.11+），人工断点采用静态 `interrupt_after` + `update_state` 注入编辑实现。各阶段事件经 SSE 流式推送前端。

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
3. 可自定义 model、base_url、temperature、max_tokens（默认 10000）

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET / POST | `/api/novels` | 项目列表 / 创建 |
| DELETE | `/api/novels/:id` | 删除项目 |
| GET / PUT | `/api/novels/:id/outline` | 获取 / 保存大纲 |
| GET / PUT | `/api/novels/:id/outline/section/:sid/content` | 获取 / 保存正文 |
| GET / PUT | `/api/novels/:id/characters` | 角色 |
| GET / PUT | `/api/novels/:id/world` | 世界观 |
| GET / POST / PUT / DELETE | `/api/novels/:id/snapshots` | 便签快照（含 `/:sid/placements` 定位反查） |
| GET / POST / PUT / DELETE | `/api/novels/:id/events` | 全局事件 |
| GET / PUT | `/api/novels/:id/canvas/:nodeId` | 节点画板 |
| GET / POST / PUT / DELETE | `/api/novels/:id/styles` | 文风 |
| POST | `/api/novels/:id/agent/plan` | 启动流水线，生成计划并暂停（SSE） |
| POST | `/api/novels/:id/agent/resume` | 恢复流水线：确认计划 / 修订 / 润色（SSE） |
| POST | `/api/novels/:id/agent/summrize` | 生成摘要 |
| GET / DELETE | `/api/novels/:id/agent/logs` | 运行日志列表 / 单条 / 删除 |

## 数据存储

```
backend/data/
├── checkpoints.sqlite      # LangGraph 流水线状态（跨请求恢复）
├── chroma/                 # ChromaDB 向量库
└── {novel_id}/
    ├── meta.json           # 项目元信息
    ├── outline.json        # 大纲树（卷→章→节）
    ├── characters.json     # 角色卡片
    ├── world_settings.json # 世界观设定
    ├── snapshots.json      # 便签快照（角色/设定历史状态）
    ├── events.json         # 全局事件
    ├── summaries.json      # 已完成章节摘要
    ├── sections/           # 各节正文 .txt
    ├── canvas/             # 各节点画板 <nodeId>.json
    ├── styles/             # 文风
    └── logs/               # 流水线运行日志 <run_id>.json
```

## 测试

```bash
python test_all.py
```

> 离线环境可设 `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` 跳过 RAG 模型联网下载。
