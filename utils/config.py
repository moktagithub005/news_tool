# utils/config.py
"""
Configuration module
- Loads environment variables securely
- Defines project paths and constants
- Used across all modules
"""

import os
from dotenv import load_dotenv

# Load .env securely
load_dotenv(override=True)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "UPSC-News-Tool")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")  # optional

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
