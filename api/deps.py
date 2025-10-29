# api/deps.py
import os
from fastapi import Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Where we store data (aligns with your Streamlit code)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PROJECT_ROOT)                    # news_tool/
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
VECTOR_DIR = os.path.join(DATA_DIR, "vector_store")
SAVED_NOTES_PATH = os.path.join(DATA_DIR, "saved_notes.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VECTOR_DIR, exist_ok=True)

def verify_api_key(x_api_key: str = Header(None)):
    expected = os.getenv("API_KEY")
    if not expected:
        # If not set on server, reject to avoid open API
        raise HTTPException(status_code=500, detail="Server misconfigured: API_KEY not set")
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")
    return True

def add_cors(app):
    origins = os.getenv("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
