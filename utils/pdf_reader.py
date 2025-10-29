# utils/pdf_reader.py
"""
PDF extraction + UPSC-focused sectioning + summarization.

Primary strategy:
- Use PyMuPDF (fitz) to extract text quickly from each page.
- Minimal OCR fallback can be added later (pytesseract) if pages are scanned images.
- Clean junk (short lines, repeated bullets, ASCII garbage).
- Split into sections using simple keyword-based mapping to UPSC categories.
- Summarize each section using:
    1) Provided LLM (via utils.llm.get_llm) if available, otherwise
    2) TF-IDF sentence scoring fallback (fast, local).
"""

from __future__ import annotations
import re
import os
import io
import math
import statistics
from typing import List, Dict, Tuple, Optional
import fitz  # PyMuPDF

# optional imports (safe fallbacks)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except Exception:
    TfidfVectorizer = None

# try to import LLM helper if present in project
try:
    from utils.llm import get_llm
except Exception:
    get_llm = None

try:
    from utils.config import UPSC_CATEGORIES
except Exception:
    UPSC_CATEGORIES = ["polity", "economy", "international", "environment", 
                       "science_tech", "social", "security", "geography"]

# optional OCR fallback
def ocr_page_image_fallback(path: str, dpi: int = 200) -> List[str]:
    """
    Convert PDF pages to images and run pytesseract OCR.
    Requires: pdf2image, pytesseract, poppler installed in system.
    Returns list of page texts.
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except Exception:
        return []

    pages_text = []
    try:
        images = convert_from_path(path, dpi=dpi)
        for img in images:
            txt = pytesseract.image_to_string(img, lang=os.getenv("OCR_LANG", "eng"))
            pages_text.append(txt)
    except Exception:
        return []
    return pages_text


# --- helpers -----------------------------------------------------------------

MIN_SENT_LEN = 30
MAX_SENT_LEN = 800

JUNK_RE = re.compile(r"^[\W_]{1,}$")
MULTI_WHITESPACE = re.compile(r"\s{2,}")

SECTION_KEYWORDS = {
    "polity": [
        "parliament", "constitution", "supreme court", "high court", "cabinet",
        "lok sabha", "rajya sabha", "governance", "policy", "bill", "act", "ordinance"
    ],
    "economy": [
        "economy", "gdp", "reserve bank", "rbi", "inflation", "budget",
        "fiscal", "monetary", "trade", "tariff", "exports", "imports", "economic"
    ],
    "international": [
        "foreign", "treaty", "bilateral", "united nations", "us", "china", "diplomatic",
        "sanction", "embargo", "international", "neighbour", "visakhapatnam", "google"
    ],
    "environment": [
        "environment", "climate", "pollution", "biodiversity", "wildlife", "conservation",
        "forest", "rainfall", "glacier", "sea level", "coastal", "emission"
    ],
    "science_tech": [
        "space", "isro", "scientist", "research", "technology", "ai", "artificial intelligence",
        "satellite", "experiment", "innovation", "robot", "data centre"
    ],
    "social": [
        "education", "health", "welfare", "poverty", "caste", "minority", "women", "child",
        "nutrition", "social", "scheme"
    ],
    "security": [
        "defence", "army", "navy", "air force", "terror", "naxal", "border", "cyber security",
        "intelligence", "safety"
    ],
    "geography": [
        "river", "mountain", "plateau", "delta", "coast", "soil", "agriculture", "monsoon",
        "geography", "terrain"
    ]
}

# merge unknown keywords to general if nothing matches
DEFAULT_SECTION = "general"


def extract_pdf_text_bytes(file_bytes: bytes, enable_ocr: bool = False) -> Tuple[str, List[str], int]:
    """
    Extract text from PDF bytes using PyMuPDF.
    Returns (full_text, list_of_page_texts, page_count).
    
    Args:
        file_bytes: PDF file as bytes
        enable_ocr: If True, attempt OCR on failed pages (requires pytesseract)
    
    Returns:
        Tuple of (full_text, page_texts_list, page_count)
    """
    # Open PDF from bytes
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    pieces = []
    
    for pno in range(len(doc)):
        page = doc.load_page(pno)
        text = page.get_text("text")
        
        if not text or text.strip() == "":
            # fallback: try extract blocks and join
            blocks = page.get_text("blocks")
            text = "\n".join([b[4] for b in blocks if b and len(b) > 4])
        
        # If still no text and OCR enabled, try OCR
        if (not text or text.strip() == "") and enable_ocr:
            try:
                pix = page.get_pixmap()
                import pytesseract
                from PIL import Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img)
            except Exception:
                pass
        
        text = text or ""
        pages.append(text)
        pieces.append(text)
    
    full = "\n\n".join(pieces)
    page_count = len(doc)
    doc.close()
    
    return full, pages, page_count


def clean_text(text: str) -> str:
    """
    Clean junk:
      - remove very short/garbled lines
      - collapse multi-whitespace
      - fix dangling bullets
    """
    lines = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        # remove lines that are only punctuation or single characters repeated
        if JUNK_RE.match(s):
            continue
        # drop extremely short noisy lines (but keep if look like valid token)
        if len(s) < MIN_SENT_LEN:
            # allow short headlines with letters + spaces (like "India rises")
            if re.match(r"^[A-Za-z0-9][A-Za-z0-9\s:\-,'()\.]{5,}$", s):
                pass
            else:
                continue
        # normalize whitespace
        s = MULTI_WHITESPACE.sub(" ", s)
        # remove trailing bullets/garbage
        s = re.sub(r"^[\u2022•\-\*]+\s*", "", s)
        lines.append(s)
    return "\n".join(lines)


def sentence_tokenize(text: str) -> List[str]:
    """
    Lightweight sentence splitter based on punctuation.
    """
    # split on sentence ends but keep abbreviations naive handling
    s = re.split(r'(?<=[\.\?\n!])\s+(?=[A-Z0-9])', text)
    out = []
    for seg in s:
        seg = seg.strip()
        if not seg:
            continue
        if len(seg) > MAX_SENT_LEN:
            # further split long segments by comma / semicolon
            parts = re.split(r'(?<=[,;])\s+', seg)
            out.extend([p.strip() for p in parts if p.strip()])
        else:
            out.append(seg)
    return out


def section_for_sentence(sent: str) -> str:
    text = sent.lower()
    scores = {}
    for sec, keys in SECTION_KEYWORDS.items():
        for k in keys:
            if k in text:
                scores[sec] = scores.get(sec, 0) + 1
    if not scores:
        return DEFAULT_SECTION
    # return best scoring section
    best = max(scores.items(), key=lambda x: x[1])[0]
    return best


def split_into_sections(full_text: str) -> Dict[str, str]:
    """
    Heuristic: sentence-level tagging into sections. Then join into section texts.
    """
    cleaned = clean_text(full_text)
    sentences = sentence_tokenize(cleaned)
    buckets: Dict[str, List[str]] = {}
    for s in sentences:
        sec = section_for_sentence(s)
        buckets.setdefault(sec, []).append(s)
    # ensure all UPSC_CATEGORIES exist as keys
    for cat in UPSC_CATEGORIES + [DEFAULT_SECTION]:
        buckets.setdefault(cat, [])
    # join
    return {k: "\n".join(v) for k, v in buckets.items() if v}


# --- summarizers -------------------------------------------------------------

def tfidf_summarize(text: str, max_sentences: int = 6) -> str:
    """
    Fallback fast summarizer using TF-IDF sentence scoring.
    """
    if not TfidfVectorizer:
        # very dumb fallback
        sents = sentence_tokenize(text)[:max_sentences]
        return "\n".join(sents)
    sents = sentence_tokenize(text)
    if not sents:
        return ""
    vec = TfidfVectorizer(stop_words="english", norm="l2")
    try:
        X = vec.fit_transform(sents)
    except Exception:
        # some tokenization issue, return first N sentences
        return "\n".join(sents[:max_sentences])
    # score by sum of tfidf per sentence
    scores = X.sum(axis=1).A1
    ranked_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    # pick top `max_sentences` in original order for readability
    top = sorted(ranked_idx[:max_sentences])
    summary = "\n".join([sents[i] for i in top])
    return summary


def llm_summarize(section_text: str, section_name: str, mode: str = "upsc") -> Optional[str]:
    """
    Use project LLM if available. This is optional — function returns None if LLM not found.
    The LLM should accept a prompt and return a short structured summary.
    """
    if get_llm is None:
        return None
    try:
        llm = get_llm(mode="deep")
        prompt = (
            f"Create UPSC-style concise notes for the section '{section_name}'.\n"
            "Instructions:\n"
            "- Provide a short summary (2-4 sentences),\n"
            "- List 3-6 prelims pointers (short bullets),\n"
            "- Suggest 2 mains angles (one-liners),\n"
            "- Provide 2 interview/discussion questions.\n\n"
            "Section text:\n" + section_text[:12000]
        )
        # We call a generic `generate` or `chat` method if present.
        # The actual implementation/method name may vary per your utils.llm; we attempt common methods.
        if hasattr(llm, "generate"):
            out = llm.generate(prompt)
            # out may be an object — try to extract text
            if isinstance(out, str):
                return out
            if hasattr(out, "generations"):
                # langchain-style
                try:
                    return out.generations[0][0].text
                except Exception:
                    return str(out)
        if hasattr(llm, "call"):
            return llm.call(prompt)
        if hasattr(llm, "chat"):
            return llm.chat(prompt)
    except Exception:
        return None
    return None


def summarize_sections(full_text: str) -> Dict[str, Dict]:
    """
    Return dict:
      { section_name: {
          "summary": "...",
          "prelims_points": [...],
          "mains_angles": [...],
          "interview_questions": [...]
        }
      }
    Uses LLM if available; otherwise TF-IDF fallback summary and light extraction heuristics.
    """
    sections = split_into_sections(full_text)
    out = {}
    for sec_name, sec_text in sections.items():
        if not sec_text.strip():
            continue
        # try LLM
        llm_out = llm_summarize(sec_text, sec_name)
        if llm_out:
            # LLM may return a plain string — store under summary key
            out[sec_name] = {
                "summary": llm_out.strip(),
                "prelims_points": [],
                "mains_angles": [],
                "interview_questions": []
            }
            continue
        # fallback
        summary = tfidf_summarize(sec_text, max_sentences=5)
        # prelist: extract important noun phrases (naive: top sentences split)
        prelims = []
        mains = []
        questions = []
        # heuristics: first sentences often headline-like
        sents = sentence_tokenize(sec_text)
        for i, s in enumerate(sents[:8]):
            if len(prelims) < 4 and len(s) < 160:
                prelims.append(s if len(s) < 200 else s[:200] + "...")
        # mains: choose top tfidf sentences if available
        mains_text = tfidf_summarize(sec_text, max_sentences=3)
        if mains_text:
            mains = [m.strip() for m in mains_text.splitlines() if m.strip()]
        # questions: turn top mains into questions
        for m in mains[:2]:
            q = f"What are the implications of '{m}' for India's policy and society?"
            questions.append(q)
        out[sec_name] = {
            "summary": summary,
            "prelims_points": prelims,
            "mains_angles": mains,
            "interview_questions": questions
        }
    return out


# --- top-level processing ----------------------------------------------------

def analyze_pdf_file(path: str) -> Dict:
    """
    Full pipeline: extract -> clean -> split -> summarize -> return structured notes.
    """
    with open(path, 'rb') as f:
        file_bytes = f.read()
    
    full_text, pages, page_count = extract_pdf_text_bytes(file_bytes)
    cleaned = clean_text(full_text)
    sections_summary = summarize_sections(cleaned)
    
    # build a ranked list of sections by amount of content (proxy for importance)
    ranked = sorted(
        sections_summary.items(),
        key=lambda kv: (len(kv[1].get("summary", "")), len(kv[1].get("prelims_points", []))),
        reverse=True
    )
    return {
        "path": path,
        "char_count": len(full_text),
        "page_count": page_count,
        "sections": {k: v for k, v in sections_summary.items()},
        "ranked_sections": [name for name, _ in ranked]
    }


# Convenience for streamlit/backend call
def analyze_pdf_bytes(file_bytes: bytes, target_path: Optional[str] = None) -> Dict:
    """
    Analyze PDF from bytes directly.
    """
    full_text, pages, page_count = extract_pdf_text_bytes(file_bytes)
    cleaned = clean_text(full_text)
    sections_summary = summarize_sections(cleaned)
    
    # build a ranked list of sections by amount of content (proxy for importance)
    ranked = sorted(
        sections_summary.items(),
        key=lambda kv: (len(kv[1].get("summary", "")), len(kv[1].get("prelims_points", []))),
        reverse=True
    )
    
    return {
        "path": target_path or "uploaded_pdf",
        "char_count": len(full_text),
        "page_count": page_count,
        "sections": {k: v for k, v in sections_summary.items()},
        "ranked_sections": [name for name, _ in ranked]
    }