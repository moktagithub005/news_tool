# api/routes/pdf.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
import traceback
import os

from utils.config import API_KEY as CONFIG_API_KEY, API_BASE_URL
from utils.pdf_reader import extract_pdf_text_bytes, split_into_sections, summarize_sections
from utils.llm import get_llm
from utils.relevance import score_relevance

router = APIRouter(prefix="/pdf", tags=["pdf"])

def _check_api_key(x_api_key: str):
    # simple check - you already have middleware but keep here for safety if used directly
    expected = os.getenv("API_KEY", CONFIG_API_KEY)
    return x_api_key == expected

@router.post("/analyze")
async def analyze_pdf(
    file: UploadFile = File(...),
    x_api_key: str | None = None,
    mode: str = "deep"   # optional: "fast" or "deep" - influences summarization
) -> Dict[str, Any]:
    """
    Upload a PDF, extract cleaned text, split into UPSC categories,
    summarize each category using Groq LLM and return ranked notes.
    """
    # API key guard
    if not _check_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    try:
        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # 1) Extract text (fast and robust using PyMuPDF)
        extraction_result = extract_pdf_text_bytes(raw_bytes)

        # Ensure we unpack the tuple correctly
        if isinstance(extraction_result, tuple):
            text, pages, page_count = extraction_result
        else:
            text = extraction_result
            pages = []
            page_count = 1

        # 2) Split into UPSC-relevant sections
        sections = split_into_sections(text)

        # 3) Prepare LLM
        llm = get_llm(model_name=os.getenv("GROQ_MODEL", None), mode=mode)

        # 4) Summarize sections - summarize_sections expects the full text string
        try:
            # Pass the full extracted text to summarize_sections
            all_summaries = summarize_sections(text)
        except Exception as e:
            print(f"[ERROR] Summarization failed: {str(e)}")
            all_summaries = {}

        summarized_sections = {}
        for cat, content in sections.items():
            if not content or not content.strip():
                continue
            
            # Get the summary from summarize_sections output
            summary_data = all_summaries.get(cat, {})
            llm_summary = summary_data.get("summary", "No summary available")
            
            # Limit content snippet based on mode
            if mode == "fast":
                content_snippet = content[:2000]
            else:
                content_snippet = content[:4000]

            # 5) Score relevance (uses your relevance scoring util)
            try:
                score = score_relevance(title="", content=content)
            except Exception:
                score = 0

            summarized_sections[cat] = {
                "raw_text_snippet": content_snippet,
                "llm_summary": llm_summary,
                "relevance_score": float(score)
            }

        # 6) Rank sections by relevance_score descending
        ranked = sorted(
            [
                {"category": k, **v}
                for k, v in summarized_sections.items()
            ],
            key=lambda x: x.get("relevance_score", 0),
            reverse=True
        )

        response = {
            "ok": True,
            "page_count": page_count,
            "sections": summarized_sections,
            "ranked_sections": ranked,
            "raw_characters_extracted": len(text)
        }
        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")