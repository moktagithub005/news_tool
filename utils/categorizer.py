# utils/categorizer.py
# Robust UPSC categorizer for news articles
# - Works with Groq (Chat model) via utils.llm.get_llm()
# - Mode: "deep" (detailed STRUCTURED) or "fast" (lightweight)
# - Always returns a valid dict with required keys
# - Cleans and normalizes AI output (JSON-only), with fallbacks

from __future__ import annotations
from typing import Dict, Any, List
import re
import json

ALLOWED_CATEGORIES = {
    "polity",
    "economy",
    "international",
    "environment",
    "science_tech",
    "social",
    "security",
    "geography",
    "governance",
    "general",
}

# ---------------------------
# Utilities / Normalization
# ---------------------------

def _safe_json_extract(s: str) -> Dict[str, Any]:
    """
    Try to parse JSON from an LLM response.
    Extracts the largest {...} block if extra text surrounds it.
    Returns a dict or {}.
    """
    if not isinstance(s, str):
        return {}
    # Try direct parse
    try:
        return json.loads(s)
    except Exception:
        pass
    # Extract largest JSON object
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        chunk = s[start : end + 1]
        try:
            return json.loads(chunk)
        except Exception:
            # Attempt to fix common trailing commas or bad quotes, minimal heuristic
            chunk2 = re.sub(r",(\s*[}\]])", r"\1", chunk)
            try:
                return json.loads(chunk2)
            except Exception:
                return {}
    return {}

def _ensure_list(value) -> List[str]:
    """
    Normalize AI field to list[str].
    - None -> []
    - str  -> split by newlines/bullets
    - list -> clean each item to str
    """
    if value is None:
        return []
    if isinstance(value, list):
        out = []
        for v in value:
            if v is None:
                continue
            s = str(v).strip().strip("•- ").strip()
            if s and any(c.isalnum() for c in s):
                out.append(s)
        return out
    if isinstance(value, str):
        parts = [p.strip().strip("•- ").strip() for p in value.split("\n")]
        return [p for p in parts if p and any(c.isalnum() for c in p)]
    return []

def _normalize_category(cat: str | None, text_ctx: str = "") -> str:
    """
    Map arbitrary label to one of ALLOWED_CATEGORIES using heuristics.
    """
    if cat:
        c = cat.strip().lower().replace(" ", "_")
        if c in ALLOWED_CATEGORIES:
            return c

    txt = (text_ctx or "").lower()

    # Heuristic keyword mapping
    rules = [
        ("polity", ["parliament", "constitution", "bill", "act", "lok sabha", "rajya sabha", "supreme court", "election"]),
        ("economy", ["gdp", "inflation", "rbi", "budget", "tax", "fiscal", "repo", "bank", "economy"]),
        ("international", ["foreign policy", "un", "g20", "fta", "diplomacy", "indo-pacific", "bilateral"]),
        ("environment", ["climate", "wildlife", "pollution", "biodiversity", "cyclone", "emission", "conservation"]),
        ("science_tech", ["isro", "drdo", "ai", "quantum", "space", "research", "semiconductor", "technology", "launch"]),
        ("social", ["health", "education", "welfare", "poverty", "tribal", "social justice", "women", "child"]),
        ("security", ["defence", "terrorism", "border", "army", "navy", "air force", "internal security"]),
        ("geography", ["earthquake", "flood", "drought", "monsoon", "river", "mountain", "lithosphere"]),
        ("governance", ["niti aayog", "e-governance", "digital public infrastructure", "regulator", "sebi", "policy implementation"]),
    ]
    for label, keys in rules:
        if any(k in txt for k in keys):
            return label
    return "general"

def _extract_dates(text: str) -> List[str]:
    """
    Extract simple date mentions (not perfect).
    Returns list of human-readable or ISO-like dates found.
    """
    if not text:
        return []
    patterns = [
        r"\b(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b",
        r"\b(?:\d{4}-\d{2}-\d{2})\b",
        r"\b(?:\d{1,2}/\d{1,2}/\d{2,4})\b",
        r"\b(?:\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b",
    ]
    out: List[str] = []
    for p in patterns:
        out.extend(re.findall(p, text))
    # Deduplicate preserving order
    seen = set()
    uniq = []
    for d in out:
        if d not in seen:
            uniq.append(d)
            seen.add(d)
    return uniq

def _truncate(s: str, max_len: int) -> str:
    if not s:
        return ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."

# ---------------------------
# Prompts
# ---------------------------

DEEP_PROMPT = """You are an expert UPSC mentor. Given the news item below, produce STRICT JSON only.

JSON SHAPE:
{
  "title": "short, 8-14 words headline for UPSC use",
  "summary_en": "5-7 line crisp UPSC-focused summary in English",
  "prelims_points": ["3-6 factual bullets for MCQs"],
  "mains_angles": ["2-4 issue-analysis bullets for GS mains"],
  "interview_questions": ["2-3 viva-style questions"],
  "schemes_acts_policies": ["Union/State schemes, Acts, Policies, Rules"],
  "institutions": ["Courts, regulators, commissions, ministries, intl bodies"],
  "dates": ["important dates found in text, ISO or human"],
  "category": "one of: polity, economy, international, environment, science_tech, social, security, geography, governance, general"
}

STRICT RULES:
- Output ONLY valid JSON. No markdown, no commentary.
- Use arrays as arrays. If none, use [].
- Category must be exactly one of the allowed values (lower_snake).
- Keep neutral tone, exam-ready.
- Prefer India/UPSC relevance.

NEWS:
Title: {title}
Description: {description}
Content: {content}
URL: {url}
Source: {source}
"""

FAST_PROMPT = """UPSC quick triage. Return STRICT JSON only with:
{
  "title": "short headline",
  "summary_en": "2-3 lines",
  "prelims_points": ["1-3 bullets"],
  "mains_angles": ["1-2 bullets"],
  "interview_questions": [],
  "schemes_acts_policies": [],
  "institutions": [],
  "dates": [],
  "category": "polity|economy|international|environment|science_tech|social|security|geography|governance|general"
}

STRICT: JSON only, arrays as arrays, category in allowed set.

NEWS:
Title: {title}
Description: {description}
Content: {content}
URL: {url}
Source: {source}
"""

# ---------------------------
# Main entry
# ---------------------------

def auto_categorize(article: Dict[str, Any], llm, mode: str = "deep") -> Dict[str, Any]:
    """
    Return a structured UPSC dict for a single article.
    Keys returned (always):
      - summary_en (str)
      - summary_hi (str) -> "" (English only for now)
      - prelims_points (list[str])
      - mains_angles (list[str])
      - interview_questions (list[str])
      - schemes_acts_policies (list[str])
      - institutions (list[str])
      - dates (list[str])
      - category (one of ALLOWED_CATEGORIES)
    """
    title = (article.get("title") or "").strip()
    description = (article.get("description") or "").strip()
    content = (article.get("content") or "").strip()
    url = (article.get("url") or "").strip()
    source = (article.get("source") or "").strip()

    # Keep prompts within model context limits; Groq Mixtral can handle large, still be safe:
    t = _truncate(title, 400)
    d = _truncate(description, 1200)
    c = _truncate(content, 4000)

    prompt = DEEP_PROMPT if (mode or "deep").lower() == "deep" else FAST_PROMPT
    prompt_fmt = prompt.format(title=t, description=d, content=c, url=url, source=source)

    # ---- Call LLM
    try:
        resp = llm.invoke(prompt_fmt)
        raw = getattr(resp, "content", str(resp))
    except Exception as e:
        raw = ""

    data = _safe_json_extract(raw)

    # ---- Build output with safety/fallbacks
    # Fallback summary if LLM fails
    fallback_summary = t or d or c[:300]
    if not fallback_summary:
        fallback_summary = "Current affairs brief with UPSC relevance."

    # Combine text for category heuristic and dates
    text_ctx = " ".join([title, description, content])

    out: Dict[str, Any] = {
        "summary_en": str(data.get("summary_en", "") or fallback_summary),
        "summary_hi": "",  # English-only as requested
        "prelims_points": _ensure_list(data.get("prelims_points")),
        "mains_angles": _ensure_list(data.get("mains_angles")),
        "interview_questions": _ensure_list(data.get("interview_questions")),
        "schemes_acts_policies": _ensure_list(data.get("schemes_acts_policies")),
        "institutions": _ensure_list(data.get("institutions")),
        "dates": _ensure_list(data.get("dates")),
        "category": _normalize_category(data.get("category"), text_ctx=text_ctx),
    }

    # If LLM returned almost nothing, create a minimal-but-valid structure
    if not out["prelims_points"] and (title or description):
        prelims_seed = []
        if title:
            prelims_seed.append(f"Headline: {title}")
        if "rbi" in text_ctx.lower():
            prelims_seed.append("RBI-related update")
        if "supreme court" in text_ctx.lower():
            prelims_seed.append("Supreme Court judgement/update")
        out["prelims_points"] = prelims_seed[:3]

    # If mains angles empty, add a generic analytical prompt based on content
    if not out["mains_angles"] and (description or content):
        out["mains_angles"] = [
            "Explain its implications for governance and public policy.",
            "Discuss potential impact on economy and society."
        ]

    # Dates fallback
    if not out["dates"]:
        out["dates"] = _extract_dates(text_ctx)

    # Title is not part of return by contract here (news.py uses article title),
    # but if you want, you can also include a refined title here.
    # out["title"] = data.get("title") or title

    return out
