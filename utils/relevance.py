# utils/relevance.py
"""
AI-based UPSC relevance scoring with keyword fallback.
- score_relevance(text, mode): returns int 0..10
- batch_score(items, mode, text_builder): convenience helper
"""

from typing import List, Dict, Callable
import re
from utils.llm import get_llm

# --- UPSC keyword sets for fallback ---
UPSC_KEYWORDS = {
    "high": [
        # Polity / Constitution / Judiciary
        "supreme court","high court","constitution","article","bill","act","ordinance",
        "parliament","lok sabha","rajya sabha","governor","president","election commission",
        # Economy / RBI / Budget / Schemes
        "rbi","budget","gdp","inflation","fiscal deficit","monetary policy","repo rate",
        "niti aayog","gst","sebi","disinvestment","PLI scheme","jan dhan","ayushman bharat",
        # IR / Treaties / Multilateral
        "unsc","g20","fta","bilateral","indian ocean","quad","indo-pacific","border",
        # Environment / Disaster / Climate
        "environment","climate","cop","wildlife","biodiversity","pollution","cyclone","flood","forest",
        # Sci-Tech / Space / Defence
        "isro","drdo","satellite","quantum","ai","semiconductor","nuclear","missile","cybersecurity",
        # Governance / Welfare
        "scheme","policy","mission","yojana","commission","committee","tribunal",
    ],
    "medium": [
        "state government","cabinet","ministry","notification","regulation","draft","consultation","startup",
        "export","import","trade","pmi","index","rating","manufacturing","services","fdi","make in india"
    ],
    "low": [
        "celebrity","movie","cricket","football","stock tips","viral","gossip","award show","rumour"
    ],
}

def _keyword_fallback_score(text: str) -> int:
    """Rough 0..10 score from keyword counts (used if AI fails)."""
    if not text:
        return 0
    t = text.lower()
    hi = sum(1 for k in UPSC_KEYWORDS["high"] if k in t)
    med = sum(1 for k in UPSC_KEYWORDS["medium"] if k in t)
    lo = sum(1 for k in UPSC_KEYWORDS["low"] if k in t)

    base = min(10, hi * 2 + med)  # max clamp
    penalty = min(3, lo)          # downweight obvious non-UPSC noise
    score = max(0, min(10, base - penalty))
    return score

AI_INSTRUCTIONS = """You are an UPSC mentor. Rate the UPSC exam relevance of the given news item on a scale of 0–10.
Consider:
- Governance/Policy/Law, Supreme Court/Judiciary, Constitution, Schemes, Economy/RBI/Budget, IR (UN/G20/FTA), Environment/Disaster/Climate, Science/Tech/ISRO/Defence
- GS2 & GS3 weight highest; national impact > state > local; official/government sources > corporate PR.
- Penalize sports/celebrity/entertainment/viral/stock-tip items.

Return ONLY a number 0..10. No text, no labels.
"""

def _parse_score(text: str) -> int:
    m = re.search(r"(\d{1,2})", text or "")
    if not m:
        return 0
    val = int(m.group(1))
    return max(0, min(10, val))

def score_relevance(text: str, mode: str = "deep") -> int:
    """
    mode: 'fast' (title/desc) or 'deep' (full content). Caller chooses what to pass as `text`.
    """
    try:
        llm = get_llm()
        prompt = f"{AI_INSTRUCTIONS}\n\nNews content:\n{text[:6000]}"  # safety cap
        resp = llm.invoke(prompt)
        ai_score = _parse_score(getattr(resp, "content", str(resp)))
        if ai_score == 0:
            return _keyword_fallback_score(text)
        return ai_score
    except Exception:
        return _keyword_fallback_score(text)

def batch_score(
    items: List[Dict],
    mode: str,
    text_builder: Callable[[Dict], str]
) -> List[int]:
    scores = []
    for it in items:
        txt = text_builder(it)
        scores.append(score_relevance(txt, mode=mode))
    return scores
