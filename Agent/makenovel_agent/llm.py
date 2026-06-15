"""LLM 客户端 — 基于 DeepSeek API（兼容 OpenAI SDK）"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional

from openai import OpenAI


@dataclass
class LLMConfig:
    """LLM 配置"""

    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096

    def validate(self) -> bool:
        return bool(self.api_key)


class LLMClient:
    """DeepSeek LLM 客户端（OpenAI 兼容）"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """发送聊天请求并返回响应文本"""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
        )
        return response.choices[0].message.content or ""

    def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """发送聊天请求，期望返回 JSON"""
        text = self.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return self._parse_json(text)

    def _parse_json(self, text: str) -> dict:
        """从 LLM 返回文本中提取 JSON"""
        text = text.strip()
        # 处理 markdown 代码块
        if text.startswith("```"):
            lines = text.split("\n")
            # 移除第一行 ```json 和最后一行 ```
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取 {...} 块
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"无法从 LLM 响应中解析 JSON: {text[:500]}")


def get_default_client(api_key: Optional[str] = None) -> LLMClient:
    """获取默认配置的 LLM 客户端"""
    config = LLMConfig()
    if api_key:
        config.api_key = api_key
    return LLMClient(config)
