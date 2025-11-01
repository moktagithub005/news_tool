# utils/api_client.py
"""
Simple API client used by the Streamlit frontend to talk to the FastAPI backend.

Behavior:
- Reads API_BASE_URL and API_KEY from environment (supports Render/containers)
- Sends header "x-api-key" (lowercase) which matches FastAPI's check
- Supports GET, POST (json / files / form-data) and DELETE
- Normalizes responses into dict: {"count": int, "items": list, "raw": <raw payload>}
- Optional DEBUG via env var DEBUG_API_CLIENT=1
"""

import os
import requests
from typing import Dict, Any, Optional

# load env from .env when running locally (safe noop in container)
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except Exception:
    # dotenv may not be present in minimal containers — that's fine
    pass

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
DEBUG = os.getenv("DEBUG_API_CLIENT", "") not in ("", "0", "false", "False")

def _debug(*args, **kwargs):
    if DEBUG:
        print("[api_client DEBUG]", *args, **kwargs)

# Build default headers (do NOT raise if API_KEY missing — allow server to handle auth)
DEFAULT_HEADERS: Dict[str, str] = {}
if API_KEY:
    DEFAULT_HEADERS["x-api-key"] = API_KEY

def _normalize_payload(resp: requests.Response) -> Dict[str, Any]:
    """Return normalized dict with keys: count, items, raw"""
    try:
        payload = resp.json()
    except ValueError:
        return {"count": 0, "items": [], "error": "Invalid JSON from API", "raw_text": resp.text}

    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("results") or payload.get("articles") or []
        # defensive: coerce non-list to list
        if not isinstance(items, list):
            try:
                items = list(items)
            except Exception:
                items = [items]
        count = payload.get("count", len(items))
        return {"count": int(count or 0), "items": items, "raw": payload}
    elif isinstance(payload, list):
        return {"count": len(payload), "items": payload, "raw": payload}
    else:
        return {"count": 0, "items": [], "raw": payload}

def _full_url(path: str) -> str:
    path = path.lstrip("/")
    return f"{API_BASE_URL}/{path}"

def get(path: str, params: Optional[Dict] = None, headers: Optional[Dict] = None, timeout: int = 30):
    url = _full_url(path)
    hdr = {**DEFAULT_HEADERS, **(headers or {})}
    _debug("GET", url, "params=", params, "headers=", hdr)
    try:
        resp = requests.get(url, headers=hdr, params=params, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        _debug("GET error:", e)
        return {"count": 0, "items": [], "error": str(e), "raw": None}
    return _normalize_payload(resp)

def post(path: str, json: Optional[Dict] = None, files: Optional[Dict] = None, data: Optional[Dict] = None, headers: Optional[Dict] = None, timeout: int = 60):
    """
    POST helper:
      - json => sends application/json
      - files => multipart/form-data with files (use {"file": open(..., "rb")})
      - data => form fields for multipart or x-www-form-urlencoded posts
    """
    url = _full_url(path)
    hdr = {**DEFAULT_HEADERS, **(headers or {})}
    _debug("POST", url, "json_present=", json is not None, "files_present=", files is not None, "hdr=", hdr)

    try:
        if json is not None:
            hdr["Content-Type"] = "application/json"
            resp = requests.post(url, headers=hdr, json=json, timeout=timeout)
        elif files is not None:
            # requests will set multipart content-type automatically
            resp = requests.post(url, headers=hdr, files=files, data=data or {}, timeout=timeout)
        else:
            # form-encoded
            resp = requests.post(url, headers=hdr, data=data or {}, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        _debug("POST error:", e, "response_text:", getattr(e, "response", None) and e.response.text)
        return {"count": 0, "items": [], "error": str(e), "raw": None}

    return _normalize_payload(resp)

def delete(path: str, headers: Optional[Dict] = None, timeout: int = 30):
    url = _full_url(path)
    hdr = {**DEFAULT_HEADERS, **(headers or {})}
    _debug("DELETE", url, "hdr=", hdr)
    try:
        resp = requests.delete(url, headers=hdr, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        _debug("DELETE error:", e)
        return {"ok": False, "error": str(e), "raw": None}

    # try JSON else raw
    try:
        return resp.json()
    except ValueError:
        return {"ok": True, "raw": resp.text}
