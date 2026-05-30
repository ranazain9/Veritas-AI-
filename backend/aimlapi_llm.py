"""
AIML API chat client for Veritas AI.

Uses langchain-openai against the AI/ML API (OpenAI-compatible) so we stay
compatible with langgraph 1.x / langchain-core 1.4+ without langchain-aimlapi's
legacy pin on langchain-core 0.3.x.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

AIMLAPI_HEADERS = {
    "HTTP-Referer": "https://github.com/veritas-ai/veritas-ai",
    "X-Title": "Veritas AI",
}


def _aiml_base_url() -> str:
    return os.getenv("AIMLAPI_API_BASE", "https://api.aimlapi.com/v1").rstrip("/")


def ChatAimlapi(**kwargs) -> ChatOpenAI:
    """Return a chat model configured for AI/ML API (AIMLAPI)."""
    params = {
        "model": kwargs.pop("model", "gpt-4o"),
        "api_key": kwargs.pop("api_key", None) or os.getenv("AIMLAPI_API_KEY", ""),
        "base_url": kwargs.pop("base_url", None) or _aiml_base_url(),
        "default_headers": kwargs.pop("default_headers", AIMLAPI_HEADERS),
        "temperature": kwargs.pop("temperature", 0.1),
    }
    params.update(kwargs)
    return ChatOpenAI(**params)
