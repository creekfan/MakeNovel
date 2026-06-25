# AGENTS.md — NovelAgent Coding Guide

## Project Overview

AI-powered novel writing tool. The backend drives a LangGraph ReAct agent (`backend/app/agent.py`) that writes section content using tools (outline/characters/world/summaries/RAG memory).
Two-tier architecture: FastAPI backend (`backend/`), React+Vite frontend (`frontend/`).

---

## Build / Lint / Test Commands

### Python (Backend)

```bash
# Run all tests (backend API integration tests, 24 cases)
python test_all.py

# Run backend manually
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

There is no pytest, no linter config (no ruff/black/flake8), no type checker config. The test suite is a single `test_all.py` script using `fastapi.testclient.TestClient`.

### Frontend

```bash
cd frontend
npm run dev      # Start Vite dev server (port 3001)
npm run build    # tsc && vite build
npm run preview  # Vite preview build
```

No lint or test commands exist in `package.json` (no ESLint, no Vitest, no Playwright).

### Starting Everything

```bash
start.bat        # Windows double-click: uvicorn + npm run dev
```

---

## Code Style Guidelines

### Python

**Imports:** stdlib first, then third-party, then local. No blank lines between groups if all fit naturally. Example:
```python
import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import storage
```

**Types:** Always annotate function signatures. Use `Optional[X]` (not `X | None`) for consistency with existing code, except in `| None` return types for simple cases like `dict | None`. Use Pydantic `BaseModel` for all data models (both backend routers and Agent models). Use `Field(description=...)` on every field.

**Naming:**
- Classes: `PascalCase` (`NovelAgentPipeline`, `LLMClient`, `PreparationResult`)
- Functions/methods: `snake_case` (`run_pipeline`, `_load_json`, `get_outline`)
- Variables: `snake_case` (`novel_id`, `outline_data`)
- Constants: `UPPER_SNAKE_CASE` (`SUMMARIZE_SYSTEM_PROMPT`, `DATA_DIR`)
- Private methods: prefix `_` (`_prepare_with_llm`, _novel_dir`)

**Formatting:** 4-space indentation. Max line length ~100 (no explicit config). Strings in double quotes preferred but single quotes appear in some files — be consistent with surrounding code.

**Docstrings:** Module-level docstrings in `"""triple double quotes"""`. Functions may have docstrings for non-obvious logic; class docstrings one-liner.

**Error handling:** Raise `HTTPException` in routers with status code and message. Raise `ValueError` in Agent code. No custom exception classes. Use early returns/guards for validation.

**Pydantic models:** Use `model_dump()` (not `.dict()`) for serialization. Use `model_rebuild()` for forward references. Use `from __future__ import annotations` in model files. Use `ClassVar` for class-level constants.

**Type annotations in Agent models:** Use `Literal` for constrained string fields. Use `list[X]` (not `List[X]`) and `dict[X, Y]` (not `Dict[X, Y]`). Use `Optional[X]` for nullable fields.

**Path handling:** Always use `pathlib.Path`, never `os.path`. Use `Path(__file__).parent` for relative paths.

**JSON I/O:** Use `json.dumps(data, ensure_ascii=False, indent=2)` for writing. Use `read_text(encoding="utf-8")` / `write_text(..., encoding="utf-8")`.

**Module structure:** `backend/` uses relative imports (`from .. import storage`). `Agent/` uses absolute imports within the package (`from .models.character import ...`). Router files in `backend/routers/` import from `..storage`.

### TypeScript / React (Frontend)

**Imports:** React/third-party first, then local. No blank lines between groups. Named exports for stores and API, default exports for pages/components.
```typescript
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api, Novel } from "../api/client";
import { useThemeStore } from "../store/theme";
```

**Types:** Use `interface` for object shapes. Use `type` for unions/aliases. Annotate state variables explicitly with generics (`useState<Novel[]>([])`).

**Naming:**
- Components: `PascalCase` (`HomePage`, `EditorPage`, `StepIndicator`)
- Functions: `camelCase` (`handleCreate`, `runPipelineStream`, `doSave`)
- Interfaces: `PascalCase` (`LLMSettings`, `PipelineStep`, `OutlineNode`)
- Stores: camelCase with `Store` suffix in name (`useThemeStore`, `useSettingsStore`)

**Formatting:** Single quotes for imports. 2-space indentation. Semicolons required. No trailing commas.

**React patterns:**
- Default export for page components
- Zustand for state management (`create<T>(...)`)
- `useRef` for holding mutable values without re-render
- `useCallback` for stable function references when passed as deps
- Avoid prop drilling — use zustand stores for global state
- Inline styles for layout (`style={{ }}`), CSS classes for reusable styles

**API client:** Centralized `api` object in `client.ts` using a generic `request<T>()` wrapper around `fetch`. All endpoints are methods on namespaced objects (`api.novels.list()`, `api.outline.get()`).

**Async patterns:** `async/await` everywhere. SSE streaming uses `ReadableStream` via `fetch` + `getReader()`.

### General

**No linting/formatting tools are configured.** Code should match the existing style of the file being edited.
- *Python:* Follow patterns in `backend/routers/`, `backend/app/`, `backend/storage.py`
- *TypeScript:* Follow patterns in `frontend/src/`

**Testing:** All tests live in `test_all.py` (backend integration). No unit tests exist for the Agent or frontend. Test pattern: define `test(name, fn)` wrapper, use `fastapi.testclient.TestClient`, print PASS/FAIL manually.

**Commit style:** Short imperative messages in Chinese or English, ~50 chars. Examples: `fix: 删除项目时清理角色数据`, `add outline tree validation`.

**Pre-commit:** No pre-commit hooks configured. No CI configuration.
