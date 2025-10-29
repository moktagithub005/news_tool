# utils/llm.py
"""
Backend-safe LLM factory.
Replaces streamlit caching with functools.lru_cache so API can import it
without Streamlit dependency or version issues.
"""

import os
from functools import lru_cache
from typing import Any, Optional

# Try to import Groq Chat; fall back to OpenAI if not available
try:
    from langchain_groq import ChatGroq
except Exception:
    ChatGroq = None

try:
    from langchain_openai import OpenAI
except Exception:
    OpenAI = None


@lru_cache(maxsize=4)
def get_llm(model_name: Optional[str] = None, provider: Optional[str] = None, temperature: float = 0.2) -> Any:
    """
    Return an LLM instance. Cached to avoid reinitialization across calls.
    provider: 'groq' or 'openai' (auto-detected from env if None)
    """
    # Decide provider
    provider_env = (provider or os.getenv("LLM_PROVIDER") or "").lower()

    if not provider_env:
        if os.getenv("GROQ_API_KEY"):
            provider_env = "groq"
        elif os.getenv("OPENAI_API_KEY"):
            provider_env = "openai"

    # Groq provider
    if provider_env == "groq" and ChatGroq is not None:
        api_key = os.getenv("GROQ_API_KEY")
        model = model_name or os.getenv("GROQ_MODEL", "mixtral-8x7b")
        # ChatGroq constructor args differ by library version — adapt if needed
        try:
            return ChatGroq(api_key=api_key, model=model, temperature=temperature)
        except TypeError:
            # older/newer signature fallback
            return ChatGroq(model=model, api_key=api_key, temperature=temperature)

    # OpenAI fallback
    if OpenAI is not None and (provider_env == "openai" or provider_env == ""):
        api_key = os.getenv("OPENAI_API_KEY")
        model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # change default if you want
        return OpenAI(temperature=temperature, openai_api_key=api_key)

    # If no provider available, raise helpful error
    raise RuntimeError("No supported LLM provider found. Set GROQ_API_KEY or OPENAI_API_KEY and install the provider package.")
