# MakeNovel

AI 辅助长篇小说创作桌面应用。提供结构化大纲规划、角色与世界构建、AI 协同写作（创作/润色/改写/审查/头脑风暴），以及 Agent 自动写作闭环。

## 功能特性

- **层级大纲管理** — 卷 → 章 → 节三级树形结构，可视化编辑与排序
- **角色系统** — 角色档案（性别/年龄/性格/外貌/背景）、角色弧光、角色关系网络
- **世界观构建** — 7 种分类：地点、势力、规则、种族、物品、职业、历史
- **AI 协同写作** — 6 种动作：创作、润色、改写、审查、头脑风暴、自动摘要
- **Agent 模式** — 自动执行"写 → 审 → 改 → 润 → 结束"完整闭环
- **PreWrite 推荐** — 写前自动推荐应注入上下文的角色与设定
- **RAG 检索增强** — 向量检索历史相关章节作为写作上下文
- **TipTap 富文本编辑器** — 所见即所得，自动保存，字数统计
- **AI 闲聊** — 独立聊天面板，可咨询写作问题

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy (async) + SQLite |
| LLM | LiteLLM (支持 OpenAI / Anthropic / DeepSeek / Ollama / Gemini) |
| 前端 | Next.js 16 + React 19 + TypeScript |
| 编辑器 | TipTap (基于 ProseMirror) |
| 状态管理 | Zustand (前端 settings 持久化到 localStorage) |
| 样式 | Tailwind CSS 4 |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- (可选) CUDA GPU，用于本地 Ollama

### 安装

```bash
# 克隆项目
git clone https://github.com/creekfan/MakeNovel.git
cd MakeNovel

# 安装 Python 依赖
cd backend
pip install -r requirements.txt

# 配置 LLM API Key
cp .env.example .env
# 编辑 .env，填入你要使用的 LLM 提供商的 API Key

# 安装前端依赖
cd ../frontend
npm install
```

### 启动

```bash
# 在项目根目录
npm run dev
```

- 后端：http://localhost:8000
- 前端：http://localhost:3000

或在设置页面中配置 LLM 提供商（API Key 仅存储在浏览器 localStorage，不上传服务器）。

### 单独启动

```bash
# 仅后端
npm run dev:backend
# 或: cd backend && python -m uvicorn main:app --reload --port 8000

# 仅前端
npm run dev:frontend
# 或: cd frontend && npm run dev
```

## 使用流程

1. **创建设置** — 在设置页配置 LLM 提供商和模型
2. **创建小说** — 填写标题、类型、简介
3. **构建世界观** — 添加角色和世界观设定
4. **规划大纲** — 建立卷→章→节三级大纲树
5. **开始写作** — 进入章节编辑器：
   - 使用 **PreWrite** 智能选择上下文
   - 点击 **AI 创作** 自动生成内容
   - 使用 **审查** 检查质量问题
   - 使用 **润色** 提升文笔
   - 或者开启 **Agent 模式** 全自动完成

## 数据库导出

```bash
python export_db.py output.txt
```

将数据库中的小说、角色、设定、大纲等全部内容导出为可读的中文文本文件。

## 配置

通过 `backend/.env` 文件或前端设置页面配置 LLM 提供商：

| 提供商 | 环境变量 |
|--------|----------|
| OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| Anthropic | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| DeepSeek | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` |
| Ollama | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL` |

默认提供商：`DEFAULT_LLM_PROVIDER=openai`

## License

MIT
