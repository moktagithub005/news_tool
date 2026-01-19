# utils/relevance.py

from typing import List, Dict, Any
import re

# -----------------------------
# Keyword-based UPSC relevance
# -----------------------------

UPSC_KEYWORDS = {
    "polity": ["constitution", "supreme court", "parliament", "article", "amendment"],
    "economy": ["gdp", "inflation", "rbi", "budget", "fiscal", "monetary"],
    "environment": ["climate", "biodiversity", "pollution", "environment"],
    "science_tech": ["isro", "ai", "technology", "research", "satellite"],
    "international": ["un", "foreign", "bilateral", "global", "treaty"],
    "security": ["defence", "terror", "border", "cyber"],
    "social": ["education", "health", "poverty", "women", "children"],
    "geography": ["river", "mountain", "climate zone", "soil"]
}

# -----------------------------
# Core relevance scorer
# -----------------------------

def score_text_relevance(text: str) -> float:
    if not text:
        return 0.0

    text_lower = text.lower()
    score = 0

    for keywords in UPSC_KEYWORDS.values():
        for kw in keywords:
            if kw in text_lower:
                score += 1

    # Normalize
    return round(score / 10, 2)


# -----------------------------
# PUBLIC API (used everywhere)
# -----------------------------

def score_relevance(
    sections: List[Dict[str, Any]],
    min_relevance: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Accepts a LIST of sections and returns the SAME list shape
    with 'relevance' added and filtered.
    """

    if not sections or not isinstance(sections, list):
        return []

    scored: List[Dict[str, Any]] = []

    for sec in sections:
        if not isinstance(sec, dict):
            continue

        text = sec.get("text", "")
        relevance = score_text_relevance(text)

        sec_out = dict(sec)
        sec_out["relevance"] = relevance

        if relevance >= min_relevance:
            scored.append(sec_out)

    # Sort highest relevance first
    scored.sort(key=lambda x: x.get("relevance", 0), reverse=True)

    return scored
