import json
from datetime import datetime
from typing import AsyncGenerator, Optional

from langchain_openai import ChatOpenAI

from .. import storage
from .pipeline import build_graph, get_saver


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _section_title(novel_id: str, section_id: str) -> str:
    return storage.find_node_title(novel_id, section_id)


class NovelAgent:
    """写作流水线 runner：plan → write → review →（revise｜polish）→ save。"""

    def __init__(self, api_key: str, base_url: str, model: str, temperature: float = 0.7, max_tokens: int = 10000):
        self.model = model
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _config(self, run_id: str):
        return {"configurable": {"thread_id": run_id}, "recursion_limit": 50}

    def _init_log(self, novel_id: str, run_id: str, section_id: str, instruction: str):
        storage.save_agent_log(novel_id, run_id, {
            "run_id": run_id,
            "section_id": section_id,
            "section_title": _section_title(novel_id, section_id),
            "instruction": instruction,
            "model": self.model,
            "started_at": datetime.now().isoformat(),
            "finished_at": "",
            "status": "running",
            "events": [],
            "final_content": "",
        })

    def _finalize_log(self, novel_id: str, run_id: str, status: str, final: str = ""):
        log = storage.get_agent_log(novel_id, run_id) or {}
        log["status"] = status
        log["finished_at"] = datetime.now().isoformat()
        if final:
            log["final_content"] = final
        storage.save_agent_log(novel_id, run_id, log)

    def _progress(self, chunk: dict):
        """把一个节点更新翻译成 SSE（若有）。"""
        events = []
        for node, delta in chunk.items():
            if not isinstance(delta, dict):
                continue
            if node == "plan":
                events.append(_sse({"step": "plan", "status": "done", "message": "统筹计划完成", "plan": delta.get("plan", {})}))
            elif node == "write":
                events.append(_sse({"step": "write", "status": "done", "message": f"草稿完成（{len(delta.get('draft',''))}字）"}))
            elif node == "review":
                rv = delta.get("review", {})
                events.append(_sse({"step": "review", "status": "done",
                                    "message": f"审查完成（{len(rv.get('issues', []))}个问题）", "review": rv}))
            elif node == "revise":
                events.append(_sse({"step": "revise", "status": "done", "message": f"修订完成（{len(delta.get('draft',''))}字）"}))
            elif node == "polish":
                events.append(_sse({"step": "polish", "status": "done", "message": f"润色完成（{len(delta.get('final',''))}字）"}))
            elif node == "save":
                events.append(_sse({"step": "save", "status": "done", "message": "已保存"}))
        return events

    async def start_plan(
        self,
        novel_id: str,
        section_id: str,
        instruction: str,
        style_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        run_id = f"{section_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self._init_log(novel_id, run_id, section_id, instruction)
        try:
            saver = await get_saver()
            graph = build_graph(self.llm, saver)
            config = self._config(run_id)
            initial = {
                "novel_id": novel_id,
                "section_id": section_id,
                "style_id": style_id,
                "instruction": instruction,
                "run_id": run_id,
            }
            yield _sse({"step": "init", "status": "running", "message": "进入计划阶段...", "thread_id": run_id})
            async for chunk in graph.astream(initial, config=config, stream_mode="updates"):
                if isinstance(chunk, dict):
                    for ev in self._progress(chunk):
                        yield ev
            snapshot = await graph.aget_state(config)
            plan = (snapshot.values or {}).get("plan", {}) if snapshot else {}
            yield _sse({"step": "await_plan", "status": "await", "thread_id": run_id,
                        "message": "计划已生成，请确认或编辑后继续", "plan": plan})
        except Exception as e:
            self._finalize_log(novel_id, run_id, "error")
            yield _sse({"step": "error", "status": "error", "message": str(e), "thread_id": run_id})

    async def resume(
        self,
        novel_id: str,
        thread_id: str,
        action: str,
        edited_plan: Optional[dict] = None,
        edited_draft: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        run_id = thread_id
        try:
            saver = await get_saver()
            graph = build_graph(self.llm, saver)
            config = self._config(run_id)

            update: dict = {}
            if action == "confirm_plan":
                if isinstance(edited_plan, dict):
                    update["plan"] = edited_plan
            elif action == "revise":
                update["action"] = "revise"
                if edited_draft is not None:
                    update["draft"] = edited_draft
            else:  # polish / go_polish
                update["action"] = "polish"
                if edited_draft is not None:
                    update["draft"] = edited_draft

            if update:
                await graph.aupdate_state(config, update)

            yield _sse({"step": "resume", "status": "running", "message": f"继续：{action}", "thread_id": run_id})
            async for chunk in graph.astream(None, config=config, stream_mode="updates"):
                if isinstance(chunk, dict):
                    for ev in self._progress(chunk):
                        yield ev

            snapshot = await graph.aget_state(config)
            values = (snapshot.values or {}) if snapshot else {}
            if snapshot and snapshot.next:
                # 仍有后续 → 停在 review 断点
                yield _sse({"step": "await_review", "status": "await", "thread_id": run_id,
                            "message": "草稿与审查已完成，请选择修订或润色",
                            "draft": values.get("draft", ""), "review": values.get("review", {})})
            else:
                final = values.get("final", "") or values.get("draft", "")
                self._finalize_log(novel_id, run_id, "done", final)
                yield _sse({"step": "complete", "status": "done", "message": "流水线完成", "final_content": final})
        except Exception as e:
            self._finalize_log(novel_id, run_id, "error")
            yield _sse({"step": "error", "status": "error", "message": str(e), "thread_id": run_id})
