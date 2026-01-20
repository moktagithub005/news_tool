# utils/llm.py
"""
Backend-safe LLM factory.
Replaces streamlit caching with functools.lru_cache so API can import it
without Streamlit dependency or version issues.
"""

import os
import logging
from functools import lru_cache
from typing import Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Try to import Groq Chat; fall back to OpenAI if not available
try:
    from langchain_groq import ChatGroq
    logger.info("✅ ChatGroq imported successfully")
except Exception as e:
    logger.warning(f"❌ Failed to import ChatGroq: {e}")
    ChatGroq = None

try:
    from langchain_openai import ChatOpenAI
    logger.info("✅ ChatOpenAI imported successfully")
except Exception as e:
    logger.warning(f"❌ Failed to import ChatOpenAI: {e}")
    ChatOpenAI = None


@lru_cache(maxsize=4)
def get_llm(model_name: Optional[str] = None, provider: Optional[str] = None, temperature: float = 0.2) -> Any:
    """
    Return an LLM instance. Cached to avoid reinitialization across calls.
    provider: 'groq' or 'openai' (auto-detected from env if None)
    """
    logger.info("=== get_llm() called ===")
    
    # Get API keys directly (don't rely on config.py imports which might fail)
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    logger.info(f"GROQ_API_KEY available: {bool(groq_key)}")
    logger.info(f"OPENAI_API_KEY available: {bool(openai_key)}")
    
    # Decide provider - PRIORITIZE OPENAI IN CLOUD
    provider_env = (provider or os.getenv("LLM_PROVIDER") or "").lower()
    logger.info(f"Provider preference: {provider_env or 'auto-detect'}")

    if not provider_env:
        # Auto-detect: Try OpenAI first (more reliable in cloud), then Groq
        if openai_key and ChatOpenAI is not None:
            provider_env = "openai"
            logger.info("Auto-detected: Using OpenAI (cloud-friendly)")
        elif groq_key and ChatGroq is not None:
            provider_env = "groq"
            logger.info("Auto-detected: Using Groq")
        elif openai_key:
            provider_env = "openai"
            logger.info("Auto-detected: Using OpenAI (Groq not available)")
        elif groq_key:
            provider_env = "groq"
            logger.info("Auto-detected: Using Groq (OpenAI not available)")

    # Try OpenAI first (more reliable)
    if provider_env == "openai" or (provider_env == "groq" and ChatGroq is None and openai_key):
        if not openai_key:
            raise RuntimeError(
                "OPENAI_API_KEY not found in environment variables."
            )
        
        if ChatOpenAI is None:
            raise RuntimeError(
                "ChatOpenAI not available. Please ensure langchain-openai is installed."
            )
        
        model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        logger.info(f"Creating ChatOpenAI with model: {model}")
        
        try:
            llm = ChatOpenAI(
                temperature=temperature,
                openai_api_key=openai_key,
                model=model
            )
            logger.info("✅ ChatOpenAI created successfully")
            return llm
        except Exception as e:
            logger.error(f"❌ Failed to create ChatOpenAI: {e}")
            # If OpenAI fails and we have Groq, try it
            if groq_key and ChatGroq is not None:
                logger.info("Falling back to Groq...")
                provider_env = "groq"
            else:
                raise RuntimeError(f"Failed to initialize ChatOpenAI: {e}")

    # Groq provider (fallback)
    if provider_env == "groq":
        if not groq_key:
            raise RuntimeError(
                "GROQ_API_KEY not found in environment variables."
            )
        
        if ChatGroq is None:
            # If ChatGroq not available but we have OpenAI, use it instead
            if openai_key and ChatOpenAI is not None:
                logger.warning("ChatGroq not available, falling back to OpenAI")
                model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                llm = ChatOpenAI(
                    temperature=temperature,
                    openai_api_key=openai_key,
                    model=model
                )
                logger.info("✅ ChatOpenAI created successfully (fallback)")
                return llm
            else:
                raise RuntimeError(
                    "ChatGroq not available. Please ensure langchain-groq is installed."
                )
        
        model = model_name or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        logger.info(f"Creating ChatGroq with model: {model}")
        
        try:
            llm = ChatGroq(
                api_key=groq_key,
                model=model,
                temperature=temperature
            )
            logger.info("✅ ChatGroq created successfully")
            return llm
        except Exception as e:
            logger.error(f"❌ Failed to create ChatGroq: {e}")
            raise RuntimeError(f"Failed to initialize ChatGroq: {e}")

    # If no provider available, raise helpful error
    error_msg = (
        "No supported LLM provider found.\n\n"
        f"Current status:\n"
        f"- GROQ_API_KEY: {'✅ Found' if groq_key else '❌ Not found'}\n"
        f"- OPENAI_API_KEY: {'✅ Found' if openai_key else '❌ Not found'}\n"
        f"- ChatGroq installed: {'✅ Yes' if ChatGroq else '❌ No'}\n"
        f"- ChatOpenAI installed: {'✅ Yes' if ChatOpenAI else '❌ No'}\n"
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)