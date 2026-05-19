from __future__ import annotations

import httpx

from .config import LLM_MAX_RETRIES, LLM_TIMEOUT_SECONDS, LLM_TRUST_ENV


def openai_client_kwargs(api_key: str, base_url: str | None = None) -> dict:
    kwargs = {
        "api_key": api_key,
        "max_retries": LLM_MAX_RETRIES,
        "http_client": httpx.Client(
            timeout=LLM_TIMEOUT_SECONDS,
            trust_env=LLM_TRUST_ENV,
        ),
    }
    if base_url:
        kwargs["base_url"] = base_url
    return kwargs
