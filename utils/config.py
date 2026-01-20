# utils/config.py
"""
Configuration module
- Loads environment variables securely
- Defines project paths and constants
- Used across all modules
"""

import os
import logging
import importlib
import importlib.util

# Try to load python-dotenv dynamically to avoid static import errors in linters/editors.
_dotenv_spec = None
try:
    _dotenv_spec = importlib.util.find_spec("dotenv")
except Exception:
    _dotenv_spec = None

if _dotenv_spec is not None:
    _dotenv = importlib.import_module("dotenv")
    load_dotenv = getattr(_dotenv, "load_dotenv")
else:
    def load_dotenv(override=False, dotenv_path=None):
        """
        Minimal fallback for python-dotenv's load_dotenv to avoid ImportError.
        Reads KEY=VALUE lines from a .env file and sets them into os.environ.
        Returns True if a file was read, False otherwise.
        """
        path = dotenv_path or os.path.join(os.getcwd(), ".env")
        try:
            with open(path, encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if override or key not in os.environ:
                        os.environ[key] = val
        except FileNotFoundError:
            return False
        return True

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env securely
load_dotenv(override=True)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "UPSC-News-Tool")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")  # optional
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Add this

# DEBUG: Log which keys are found (without exposing the actual keys)
logger.info("=== ENVIRONMENT VARIABLES CHECK ===")
logger.info(f"GROQ_API_KEY found: {bool(GROQ_API_KEY)} (length: {len(GROQ_API_KEY) if GROQ_API_KEY else 0})")
logger.info(f"OPENAI_API_KEY found: {bool(OPENAI_API_KEY)} (length: {len(OPENAI_API_KEY) if OPENAI_API_KEY else 0})")
logger.info(f"NEWSAPI_KEY found: {bool(NEWSAPI_KEY)}")
logger.info("====================================")

# API
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
API_KEY = os.getenv("API_KEY", "unisole-test-key")

# Project folders
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
VECTOR_DIR = os.path.join(DATA_DIR, "vector_store")

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VECTOR_DIR, exist_ok=True)

# Models
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# UPSC Categories
UPSC_CATEGORIES = [
    "polity", "economy", "international", "environment",
    "science_tech", "social", "security", "geography"
]

# Enable LangSmith tracing if key present
if LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT