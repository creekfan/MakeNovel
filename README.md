# MakeNovel

AI 驱动的小说写作工具，基于多 Agent 管道（准备→创作→审查→修订→润色）实现结构化长篇小说创作。

## 架构

```
MakeNovel/
├── Agent/              # 核心 Agent 管道（Python）
├── backend/            # FastAPI REST API
├── frontend/           # React + TypeScript + Vite
├── migrate_db.py       # 旧版 SQLite 数据迁移脚本
├── test_all.py         # 后端测试套件（24 项）
└── start.bat           # Windows 一键启动
```

## 功能

- **项目管理** — 创建/删除小说项目
- **大纲编辑** — 卷→章→节 三级树形结构，每层可写情节概要，支持节点插入/删除/编辑
- **写作页面** — 从大纲直达编辑器，正文自动保存（1s 防抖）
- **Agent 调用** — 一键运行完整管道或单步 Agent，SSE 实时显示进度及中间产出
- **生成摘要** — LLM 归纳正文生成结构化摘要，自动标记完成并写入上下文链
- **角色卡片** — 名称/定位/外貌/性格/背景/能力/说话风格/弧光
- **世界观设定** — 7 类分类筛选（环境/势力/规则/种族/物品/职业/历史），内联编辑
- **模型设置** — API Key 安全缓存在浏览器 localStorage（Base64），支持自定义模型/base_url/参数
- **深色模式** — 跟随系统或手动切换，全局 CSS 变量

## Agent 管道

```
准备者 → 创作者 → 审查者 → 修订者 → 润色者
```

| Agent | 职责 |
|-------|------|
| Preparer | 读取大纲/前文/角色/世界观，组装写作上下文 |
| Creator | 根据上下文生成正文初稿 |
| Reviewer | 审查逻辑/角色一致性/情节漏洞 |
| Reviser | 根据审查意见修订正文 |
| Polisher | 优化文笔表达 |

## 快速开始

### 环境要求

- Python 3.11+（需安装 fastapi、uvicorn、openai、pydantic）
- Node.js 18+

### 安装

```bash
# 后端依赖
pip install fastapi uvicorn[standard] openai pydantic pyyaml

# 前端依赖
cd frontend && npm install
```

### 启动

**Windows：** 双击 `start.bat`

**手动启动：**

```bash
# 后端（端口 8001）
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload

# 前端（端口 3001）
cd frontend && npm run dev
```

打开浏览器访问 http://localhost:3001

### 配置 LLM

1. 进入任意项目 → 侧边栏「模型设置」
2. 填入 DeepSeek API Key（或其他 OpenAI 兼容 API）
3. 可自定义 model、base_url、temperature、max_tokens

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/novels` | 项目列表 |
| POST | `/api/novels` | 创建项目 |
| GET | `/api/novels/:id/outline` | 获取大纲 |
| PUT | `/api/novels/:id/outline` | 保存大纲 |
| GET | `/api/novels/:id/outline/section/:sid/content` | 获取正文 |
| PUT | `/api/novels/:id/outline/section/:sid/content` | 保存正文 |
| GET | `/api/novels/:id/characters` | 角色列表 |
| PUT | `/api/novels/:id/characters` | 保存角色 |
| GET | `/api/novels/:id/world` | 世界观列表 |
| PUT | `/api/novels/:id/world` | 保存世界观 |
| POST | `/api/novels/:id/agent/run-stream` | 流式执行完整管道（SSE） |
| POST | `/api/novels/:id/agent/single` | 执行单步 Agent |
| POST | `/api/novels/:id/agent/summarize` | 生成摘要 |

## 数据存储

项目数据以 JSON 文件存储在 `backend/data/{novel_id}/`：

```
backend/data/{id}/
├── meta.json           # 项目元信息
├── outline.json        # 大纲树
├── characters.json     # 角色卡片
├── world_settings.json # 世界观设定
├── summaries.json      # 已完成章节摘要（Agent 上下文链）
└── sections/           # 各节正文
    ├── node-1.txt
    └── ...
```

## 测试

```bash
python test_all.py
```

## License

MIT
