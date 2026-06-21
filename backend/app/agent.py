import json
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .. import storage
from .memory import embed_section
from .prompts import AGENT_SYSTEM_PROMPT
from .tools import get_all_tools


class NovelAgent:
    def __init__(self, api_key: str, base_url: str, model: str, temperature: float = 0.7, max_tokens: int = 4096):
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.tools = get_all_tools()
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=AGENT_SYSTEM_PROMPT,
        )

    async def astream(
        self,
        novel_id: str,
        section_id: str,
        instruction: str,
    ) -> AsyncGenerator[str, None]:
        def _sse(data: dict) -> str:
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        outline = storage.get_outline(novel_id) or {}
        sections = _find_sections(outline.get("volumes", []))
        section_info = sections.get(section_id, {})
        existing_content = storage.get_section_content(novel_id, section_id) or ""

        yield _sse({"step": "init", "status": "running", "message": "构建上下文..."})

        user_msg = f"## 任务\n{instruction}\n\n## 当前节\nID: {section_id}\n标题: {section_info.get('title', '')}\n概要: {section_info.get('summary', '')}\n\n"
        if existing_content:
            user_msg += f"## 已有内容（{len(existing_content)}字）\n{existing_content[:1000]}{'...' if len(existing_content) > 1000 else ''}\n"
        user_msg += "\n请先获取所需信息，然后直接创作正文。创作完成后调用 finish 工具，将正文内容作为参数传入。"

        config = RunnableConfig(
            configurable={"novel_id": novel_id, "section_id": section_id},
            recursion_limit=25,
        )

        messages = [HumanMessage(content=user_msg)]
        final_content = ""

        yield _sse({"step": "agent", "status": "running", "message": "Agent 开始执行..."})

        async for event in self.agent.astream_events(
            {"messages": messages},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            name = event.get("name", "")

            if kind == "on_chat_model_start":
                if name == "ChatOpenAI":
                    yield _sse({"step": "thinking", "status": "running", "message": "思考中..."})

            elif kind == "on_chat_model_end":
                if name == "ChatOpenAI":
                    yield _sse({"step": "thinking", "status": "done", "message": "思考完成"})
                    msgs = event.get("data", {}).get("output", {})
                    if isinstance(msgs, AIMessage) and msgs.content and not msgs.tool_calls:
                        final_content = msgs.content

            elif kind == "on_tool_start":
                tool_input = event.get("data", {}).get("input", "")
                yield _sse({
                    "step": "tool_call",
                    "status": "running",
                    "tool": name,
                    "message": f"调用工具：{name}",
                    "input": str(tool_input)[:200],
                })

            elif kind == "on_tool_end":
                tool_output = event.get("data", {}).get("output", "")
                yield _sse({
                    "step": "tool_call",
                    "status": "done",
                    "tool": name,
                    "message": f"工具 {name} 执行完成",
                })
                if name == "finish":
                    final_content = tool_output if isinstance(tool_output, str) else str(tool_output)

        if not final_content:
            # fallback: grab last AI message from final state
            async for event in self.agent.astream_events(
                {"messages": messages},
                config=config,
                version="v2",
            ):
                if event.get("event") == "on_chain_end" and event.get("name") == "LangGraph":
                    data = event.get("data", {}).get("output", {})
                    if isinstance(data, dict):
                        msgs = data.get("messages", [])
                        for m in reversed(msgs):
                            if isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
                                final_content = m.content
                                break

        if final_content:
            storage.save_section_content(novel_id, section_id, final_content)
            embed_section(novel_id, section_id, section_info.get("title", ""), final_content)

        yield _sse({
            "step": "complete",
            "status": "done",
            "message": "Agent 执行完成",
            "final_content": final_content,
        })


def _find_sections(volumes: list) -> dict[str, dict]:
    result = {}
    for vol in volumes:
        for ch in vol.get("children", []):
            for sec in ch.get("children", []):
                result[sec.get("id", "")] = {
                    "title": sec.get("title", ""),
                    "summary": sec.get("summary", ""),
                    "status": sec.get("status", "planned"),
                    "volume_title": vol.get("title", ""),
                    "chapter_title": ch.get("title", ""),
                }
    return result
