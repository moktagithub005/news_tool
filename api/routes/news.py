# api/routes/news.py
# Ingest news -> UPSC structuring (deep) -> safe lists -> relevance -> ALWAYS return items

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from api.deps import verify_api_key
from api.schemas import IngestRequest, IngestResponse, IngestItem

from utils.news_fetcher import fetch_news
from utils.categorizer import auto_categorize
from utils.relevance import score_relevance
from utils.llm import get_llm

router = APIRouter(prefix="/ingest", tags=["ingest"])

# -----------------------
# Safety / Cleaning utils
# -----------------------

def _ensure_list(value) -> List[str]:
    """Normalize to list[str]; clean bullets & junk."""
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

def _str(x) -> str:
    return "" if x is None else str(x)

def _heuristic_category(text: str) -> str:
    t = (text or "").lower()
    rules = [
        ("polity",       ["parliament","constitution","bill","act","lok sabha","rajya sabha","supreme court","election"]),
        ("economy",      ["gdp","inflation","rbi","budget","tax","fiscal","repo","bank","economy"]),
        ("international",["foreign policy","un "," g20","fta","diplomacy","indo-pacific","bilateral","pakistan","china"]),
        ("environment",  ["climate","wildlife","pollution","biodiversity","cyclone","emission","forest","conservation"]),
        ("science_tech", ["isro","drdo","ai","quantum","space","research","semiconductor","technology","launch"]),
        ("social",       ["health","education","welfare","poverty","tribal","social justice","women","child","nrega"]),
        ("security",     ["defence","terrorism","border","army","navy","air force","internal security"]),
        ("geography",    ["earthquake","flood","drought","monsoon","river","mountain"]),
        ("governance",   ["niti aayog","e-governance","digital public infrastructure","sebi","regulator","implementation"]),
    ]
    for label, keys in rules:
        if any(k in t for k in keys):
            return label
    return "general"

def _fallback_points(title: str, desc: str, content: str) -> Dict[str, List[str]]:
    ctx = " ".join([title or "", desc or "", content or ""]).lower()
    prelims = []
    if title: prelims.append(f"Headline: {title}")
    if "rbi" in ctx: prelims.append("RBI-related update")
    if "supreme court" in ctx: prelims.append("Supreme Court judgement/update")
    if "bill" in ctx or "act" in ctx: prelims.append("Legislative development (Bill/Act)")
    mains = [
        "Explain implications for governance/public policy.",
        "Discuss potential impact on economy and society."
    ]
    return {
        "prelims_points": prelims[:4],
        "mains_angles": mains
    }

def _fallback_dates(text: str) -> List[str]:
    import re
    pats = [
        r"\b(?:\d{4}-\d{2}-\d{2})\b",
        r"\b(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b",
        r"\b(?:\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b",
        r"\b(?:\d{1,2}/\d{1,2}/\d{2,4})\b",
    ]
    found = []
    for p in pats:
        found += re.findall(p, text or "")
    # dedupe keep order
    out, seen = [], set()
    for d in found:
        if d not in seen:
            out.append(d); seen.add(d)
    return out

def _keyword_relevance(text: str) -> int:
    """Simple fallback relevance 1-10 using keyword hits."""
    keys = [
        "india","government","policy","scheme","supreme court","rbi","budget","parliament",
        "isro","environment","act","bill","election","gdp","inflation","security","governance"
    ]
    t = (text or "").lower()
    hits = sum(1 for k in keys if k in t)
    # map hits to 1..10
    score = 3 + min(7, hits)
    return max(1, min(10, score))


def _get_source_name(source_obj) -> str:
    """
    Normalize the 'source' field from NewsAPI article to a plain string.
    Handles: dict ({"id","name"}), tuple/list, string, None.
    Always returns a simple string (no tuples).
    """
    if source_obj is None:
        return ""
    # dict like {"id": "...", "name": "..."}
    if isinstance(source_obj, dict):
        name = source_obj.get("name") or source_obj.get("id") or ""
        return str(name) if name is not None else ""
    # tuple or list (('The Times',),)
    if isinstance(source_obj, (tuple, list)):
        if len(source_obj) == 0:
            return ""
        first = source_obj[0]
        # if nested dict
        if isinstance(first, dict):
            return _get_source_name(first)
        return str(first)
    # fallback: cast to str
    return str(source_obj)



# -----------------------
# Route
# -----------------------

@router.post("/news", response_model=IngestResponse)
def ingest_news(req: IngestRequest, _: bool = Depends(verify_api_key)):
    """
    Fetch + structure UPSC news.
    Final Output Mode = A (always return items with safe fallbacks).
    AI Clean Mode = A (sanitize lists and junk).
    """
    # 1) Fetch raw items
    try:
        articles: List[Dict[str, Any]] = fetch_news(
            query=req.query,
            days_back=req.days_back,
            page_size=req.page_size,
            use_newsapi=req.use_newsapi,
            use_pib=req.use_pib,
            use_prs=req.use_prs,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fetch error: {e}")

    if not isinstance(articles, list):
        raise HTTPException(status_code=500, detail="Fetcher returned invalid type")

    llm = get_llm()
    out: List[IngestItem] = []

    # 2) Per-article: categorize + relevance + fallbacks
    for art in articles:
        title = _str(art.get("title"))
        desc = _str(art.get("description"))
        content = _str(art.get("content"))
        url = art.get("url")
        source=_get_source_name(art.get("source"))


        # a) Try AI deep structuring
        meta: Dict[str, Any] = {}
        try:
            meta = auto_categorize(article=art, llm=llm, mode=(req.ai_mode or "deep"))
        except Exception:
            meta = {}

        # b) Clean & fallbacks (AI Clean Mode = A)
        summary_en = _str(meta.get("summary_en")) or (title or desc or content[:300] or "Current affairs brief.")
        prelims = _ensure_list(meta.get("prelims_points"))
        mains = _ensure_list(meta.get("mains_angles"))
        ivqs = _ensure_list(meta.get("interview_questions"))
        schemes = _ensure_list(meta.get("schemes_acts_policies"))
        insts = _ensure_list(meta.get("institutions"))
        dates = _ensure_list(meta.get("dates"))

        if not prelims or not mains:
            fb = _fallback_points(title, desc, content)
            if not prelims: prelims = fb["prelims_points"]
            if not mains: mains = fb["mains_angles"]
        if not dates:
            dates = _fallback_dates(" ".join([title, desc, content]))

        category = meta.get("category") or _heuristic_category(" ".join([title, desc, content]))

        # c) Relevance (deep if chosen) with fallback keyword score
        rel_text = f"{title}\n{summary_en}\n{desc}\n{content}"
        try:
            rel_mode = "deep" if (req.ai_mode or "deep").lower() == "deep" else "fast"
            rel_score = int(score_relevance(rel_text, mode=rel_mode))
            if not (1 <= rel_score <= 10):
                raise ValueError
        except Exception:
            rel_score = _keyword_relevance(rel_text)

        # d) Build schema-safe item
        item = IngestItem(
            title=title[:300],
            url=url,
            publishedAt=art.get("publishedAt"),
            source=source,
            category=category,
            relevance=int(rel_score),
            summary_en=summary_en,
            summary_hi="",  # English only for now
            prelims_points=prelims,
            mains_angles=mains,
            interview_questions=ivqs,
            schemes_acts_policies=schemes,
            institutions=insts,
            dates=dates,
        )
        out.append(item)

    # 3) Sort & cap
    out.sort(key=lambda x: int(getattr(x, "relevance", 0)), reverse=True)
    if req.page_size and isinstance(req.page_size, int):
        out = out[:max(1, req.page_size)]

    print("DEBUG ingest output count =", len(out))

    return IngestResponse(
        ok=True,
        items=out,
        count=len(out),
        message="OK"
    )
