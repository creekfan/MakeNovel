from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{Path(__file__).parent.parent.parent.parent / 'data' / 'makenovel.db'}"
    default_llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20240620"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    max_context_tokens: int = 8000
    max_output_tokens: int = 2000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
