from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DEFAULTS = {
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
        "base_url": None,
        "temperature": 0,
    },
    "groq": {
        "api_key_env": "GROQ_API_KEY",
        "model": "qwen/qwen3-32b",
        "base_url": "https://api.groq.com/openai/v1",
        "temperature": 0.1,
    },
}


def get_active_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "groq").strip().lower()


def get_llm(provider: str | None = None, request_timeout: int = 30) -> ChatOpenAI:
    provider_name = (provider or get_active_provider()).strip().lower()
    if provider_name not in DEFAULTS:
        raise ValueError(f"Unsupported LLM provider '{provider_name}'.")

    settings = DEFAULTS[provider_name]
    api_key = os.environ.get(settings["api_key_env"], "").strip()
    if not api_key:
        raise ValueError(f"Missing {settings['api_key_env']} for provider '{provider_name}'.")

    model = os.environ.get("LLM_MODEL", "").strip() or settings["model"]
    base_url = os.environ.get("LLM_BASE_URL", "").strip() or settings["base_url"]

    kwargs = {
        "model": model,
        "temperature": settings["temperature"],
        "api_key": api_key,
        "request_timeout": request_timeout,
    }
    if base_url:
        kwargs["base_url"] = base_url

    return ChatOpenAI(**kwargs)
