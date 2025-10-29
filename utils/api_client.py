# utils/api_client.py
import os
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("API_KEY", "")

if not API_KEY:
    raise ValueError("API_KEY not found! Please set in .env")

HEADERS = {"X-API-Key": API_KEY}

def get(path: str, params: Dict = None):
    url = f"{API_BASE_URL}{path}"
    response = requests.get(url, headers=HEADERS, params=params)
    return _handle_response(response)

def post(path: str, json: Dict = None, files: Dict = None, data: Dict = None):
    """
    Helper to POST to API and *normalize* the response into a dict:
    { "count": int, "items": list, "raw": <original json> }

    - Uses API_BASE_URL env var (falls back to http://api:8000)
    - Sends x-api-key header from env var API_KEY (fallback: unisole-test-key)
    - Supports JSON posts, file uploads and form-data
    """
    import os
    import requests
    from requests.exceptions import RequestException

    # Build URL
    base = os.getenv("API_BASE_URL", "http://api:8000").rstrip("/")
    if path.startswith("/"):
        url = f"{base}{path}"
    else:
        url = f"{base}/{path}"

    # Headers (API key + content-type for json)
    headers = {}
    api_key = os.getenv("API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    try:
        if json is not None:
            headers["Content-Type"] = "application/json"
            resp = requests.post(url, json=json, headers=headers, timeout=30)
        elif files:
            # multipart upload
            resp = requests.post(url, files=files, data=data or {}, headers=headers, timeout=120)
        else:
            resp = requests.post(url, data=data or {}, headers=headers, timeout=30)

        resp.raise_for_status()
    except RequestException as e:
        # Return normalized error structure so UI doesn't crash
        return {"count": 0, "items": [], "error": str(e), "raw": None}

    # Try parse JSON and normalize keys
    try:
        payload = resp.json()
    except ValueError:
        # not JSON
        return {"count": 0, "items": [], "error": "Invalid JSON from API", "raw_text": resp.text}

    # payload may be dict or list; prefer dict
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("results") or payload.get("articles") or []
        count = payload.get("count", len(items))
        # defensive: ensure items is a list
        if not isinstance(items, list):
            # if API returned single item or tuple, coerce
            try:
                items = list(items)
            except Exception:
                items = [items]
        return {"count": int(count or 0), "items": items, "raw": payload}
    else:
        # Unexpected shape (e.g., list), return it as items
        if isinstance(payload, list):
            return {"count": len(payload), "items": payload, "raw": payload}
        return {"count": 0, "items": [], "raw": payload}


def delete(path: str):
    url = f"{API_BASE_URL}{path}"
    response = requests.delete(url, headers=HEADERS)
    return _handle_response(response)

def _handle_response(response):
    if response.status_code in (200, 201):
        return response.json() if "application/json" in str(response.headers) else response.content
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")
