# utils/llm.py
"""
Backend-safe LLM factory.
Replaces streamlit caching with functools.lru_cache so API can import it
without Streamlit dependency or version issues.
"""

import os
import logging
import importlib
from functools import lru_cache
from typing import Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Try to import Groq Chat; fall back to OpenAI if not available
try:
    import importlib
    module = importlib.import_module("langchain_groq")
    ChatGroq = getattr(module, "ChatGroq", None)
    if ChatGroq:
        logger.info("✅ ChatGroq imported successfully")
    else:
        logger.warning("❌ langchain_groq imported but ChatGroq attribute not found")
except Exception as e:
    logger.warning(f"❌ Failed to import ChatGroq: {e}")
    ChatGroq = None
try:
    # Try known module paths for ChatOpenAI to avoid unresolved-import errors in editors
    ChatOpenAI = None
    try:
        module = importlib.import_module("langchain_openai")
        ChatOpenAI = getattr(module, "ChatOpenAI", None)
        if ChatOpenAI:
            logger.info("✅ ChatOpenAI imported successfully from langchain_openai")
    except Exception:
        # Fallback to langchain.chat_models (common in newer langchain versions)
        try:
            module = importlib.import_module("langchain.chat_models")
            ChatOpenAI = getattr(module, "ChatOpenAI", None)
            if ChatOpenAI:
                logger.info("✅ ChatOpenAI imported successfully from langchain.chat_models")
        except Exception as e:
            logger.warning(f"❌ Failed to import ChatOpenAI from known modules: {e}")
            ChatOpenAI = None
except Exception as e:
    logger.warning(f"❌ Unexpected error while resolving ChatOpenAI: {e}")
    ChatOpenAI = None
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
    
    # Decide provider
    provider_env = (provider or os.getenv("LLM_PROVIDER") or "").lower()
    logger.info(f"Provider preference: {provider_env or 'auto-detect'}")

    if not provider_env:
        if groq_key:
            provider_env = "groq"
            logger.info("Auto-detected: Using Groq")
        elif openai_key:
            provider_env = "openai"
            logger.info("Auto-detected: Using OpenAI")

    # Groq provider
    if provider_env == "groq":
        if not groq_key:
            raise RuntimeError(
                "GROQ_API_KEY not found in environment variables. "
                "Please set it in your Render.com dashboard under Environment Variables."
            )
        
        if ChatGroq is None:
            raise RuntimeError(
                "ChatGroq not available. Please ensure langchain-groq is installed. "
                "Check requirements.txt includes: langchain-groq>=0.0.1"
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

    # OpenAI fallback
    if provider_env == "openai" or provider_env == "":
        if not openai_key:
            raise RuntimeError(
                "OPENAI_API_KEY not found in environment variables. "
                "Please set either GROQ_API_KEY or OPENAI_API_KEY in Render.com dashboard."
            )
        
        if ChatOpenAI is None:
            raise RuntimeError(
                "ChatOpenAI not available. Please ensure langchain-openai is installed. "
                "Add to requirements.txt: langchain-openai>=0.0.5"
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
            raise RuntimeError(f"Failed to initialize ChatOpenAI: {e}")

    # If no provider available, raise helpful error
    error_msg = (
        "No supported LLM provider found.\n\n"
        "Available options:\n"
        "1. Set GROQ_API_KEY in Render.com Environment Variables\n"
        "2. Set OPENAI_API_KEY in Render.com Environment Variables\n\n"
        f"Current status:\n"
        f"- GROQ_API_KEY: {'✅ Found' if groq_key else '❌ Not found'}\n"
        f"- OPENAI_API_KEY: {'✅ Found' if openai_key else '❌ Not found'}\n"
        f"- ChatGroq installed: {'✅ Yes' if ChatGroq else '❌ No'}\n"
        f"- ChatOpenAI installed: {'✅ Yes' if ChatOpenAI else '❌ No'}\n"
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)