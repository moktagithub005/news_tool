# utils/pdf_analyzer.py
"""
PDF → UPSC Notes Analyzer (robust)
- Splits long text into chunks and analyzes per-chunk
- Merges & dedupes items
- Handles JSON wrapped in code fences
"""

from typing import Dict, List, Tuple
import json, re
from langchain_core.messages import SystemMessage, HumanMessage
from utils.llm import get_llm
from utils.config import UPSC_CATEGORIES

JSON_SCHEMA_EXAMPLE = {
  "items": [
    {
      "title": "Short title of the news/topic",
      "category": "polity|economy|international|environment|science_tech|social|security|geography",
      "relevance": 0,
      "dates": ["2025-01-18"],
      "schemes_acts_policies": [],
      "institutions": [],
      "summary_en": "",
      "summary_hi": "",
      "key_facts": [],
      "prelims_points": [],
      "mains_angles": [],
      "interview_questions": []
    }
  ]
}

def _clean_json(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*", "", s).strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    return s

def _parse_items(raw: str) -> List[dict]:
    try:
        j = json.loads(_clean_json(raw))
        return j.get("items", [])
    except Exception:
        return []

def _sys_msg():
    return SystemMessage(content=
        "You are a strict UPSC current-affairs extractor. "
        f"Categorize items into: {', '.join(UPSC_CATEGORIES)}. "
        "Return ONLY valid JSON: {items:[{title,category,relevance,dates,schemes_acts_policies, "
        "institutions,summary_en,summary_hi,key_facts,prelims_points,mains_angles,interview_questions}]}"
    )

def _user_msg(chunk: str) -> HumanMessage:
    return HumanMessage(content=f"""
From the text chunk below, extract 3–10 UPSC-relevant items.
Rank 'relevance' 0–10 (UPSC importance). If Hindi, still fill EN/HI both when possible.
Return ONLY JSON, no extra text.

Schema example (shape only):
{json.dumps(JSON_SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)}

TEXT CHUNK:
{chunk}
""")

def chunk_text(s: str, size: int = 6000, overlap: int = 300) -> List[str]:
    out = []
    i = 0
    n = len(s)
    step = max(1, size - overlap)
    while i < n:
        out.append(s[i:i+size])
        i += step
    return out

def _norm_title(t: str) -> str:
    return (t or "").strip().lower()[:120]

def analyze_pdf_text(full_text: str, language: str = "Both",
                     chunk_size: int = 6000, overlap: int = 300,
                     debug: bool = False) -> Tuple[Dict[str, List[Dict]], List[str]]:
    """
    Returns:
      - dict[category] -> items (sorted by relevance desc)
      - debug_raw: list of raw model responses for inspection
    """
    llm = get_llm()
    sys = _sys_msg()
    chunks = chunk_text(full_text, chunk_size, overlap)

    all_items: List[dict] = []
    raw_responses: List[str] = []

    for ch in chunks[:12]:  # safety cap
        resp = llm.invoke([sys, _user_msg(ch)]).content
        raw_responses.append(resp)
        items = _parse_items(resp)
        all_items.extend(items)

    # dedupe by title
    seen = set()
    uniq = []
    for it in all_items:
        key = _norm_title(it.get("title", ""))
        if key and key not in seen:
            seen.add(key)
            uniq.append(it)

    # group by category
    grouped: Dict[str, List[Dict]] = {c: [] for c in UPSC_CATEGORIES}
    grouped["general"] = []
    for it in uniq:
        cat = it.get("category", "general")
        if cat not in grouped: cat = "general"
        grouped[cat].append(it)

    for k in grouped:
        grouped[k].sort(key=lambda x: int(x.get("relevance", 0)), reverse=True)

    return grouped, raw_responses

def to_markdown(notes_by_cat: Dict[str, List[Dict]], date_str: str, paper_name: str = "") -> str:
    lines = []
    header = f"# UPSC Notes — {date_str} {('— ' + paper_name) if paper_name else ''}\n"
    lines.append(header)
    for cat, items in notes_by_cat.items():
        if not items: continue
        lines.append(f"\n## {cat.replace('_',' ').title()}\n")
        for i, it in enumerate(items, 1):
            lines.append(f"### {i}. {it.get('title','(No title)')}")
            lines.append(f"**UPSC relevance:** {it.get('relevance',0)}/10\n")
            if it.get("dates"): lines.append(f"**Dates:** {', '.join(it.get('dates', []))}")
            if it.get("schemes_acts_policies"): lines.append(f"**Schemes/Acts/Policies:** {', '.join(it.get('schemes_acts_policies', []))}")
            if it.get("institutions"): lines.append(f"**Institutions:** {', '.join(it.get('institutions', []))}")
            if it.get("summary_en"): lines.append(f"\n**Summary (EN):**\n{it['summary_en']}")
            if it.get("summary_hi"): lines.append(f"\n**सार (HI):**\n{it['summary_hi']}")
            if it.get("key_facts"): lines.append("\n**Key Facts:**\n- " + "\n- ".join(it["key_facts"]))
            if it.get("prelims_points"): lines.append("\n**Prelims Pointers:**\n- " + "\n- ".join(it["prelims_points"]))
            if it.get("mains_angles"): lines.append("\n**Mains Angles:**\n- " + "\n- ".join(it["mains_angles"]))
            if it.get("interview_questions"): lines.append("\n**Interview Questions:**\n- " + "\n- ".join(it["interview_questions"]))
            lines.append("\n---\n")
    return "\n".join(lines)

def make_mcqs_from_notes(notes_by_cat: Dict[str, List[Dict]], count: int = 10) -> str:
    llm = get_llm()
    bullets = []
    for items in notes_by_cat.values():
        for it in items:
            bullets += it.get("prelims_points", []) or it.get("key_facts", [])
    seed = "\n".join(f"- {b}" for b in bullets[:100])
    prompt = f"""
Create {count} UPSC Prelims-quality MCQs from the points below.
Each must have: stem, options (A–D), correct answer, 1–2 line explanation.
Return Markdown with [EN] and [HI] versions for each question.

Points:
{seed}
"""
    return llm.invoke(prompt).content
