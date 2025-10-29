# api/routes/export.py
from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import StreamingResponse, JSONResponse
import io
import logging
from typing import Optional
from utils.docx_exporter import export_notes_to_docx, build_docx_from_notes
from utils.config import DATA_DIR
import os
import json

router = APIRouter(prefix="/export", tags=["export"])

# Path to saved notes
SAVED_PATH = os.path.join(DATA_DIR, "saved_notes.json")

def load_saved_notes():
    """Load saved notes from JSON file."""
    if not os.path.exists(SAVED_PATH):
        logging.warning(f"Saved notes file not found: {SAVED_PATH}")
        return {}
    
    try:
        with open(SAVED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.exception(f"Failed to parse saved_notes.json: {e}")
        return {}


def _validate_api_key(x_api_key: Optional[str] = Header(None)):
    """Validate API key if configured."""
    expected = os.getenv("API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")


def convert_list_to_structured_format(notes_list: list, date: str) -> dict:
    """
    Convert list of notes into structured format for DOCX export.
    
    Args:
        notes_list: List of note items from saved_notes.json
        date: The date string
    
    Returns:
        Structured dict compatible with build_docx_from_notes
    """
    grouped = {}
    
    for item in notes_list:
        category = item.get("category", "general")
        
        if category not in grouped:
            grouped[category] = []
        
        # Convert to the format expected by docx exporter
        formatted_item = {
            "category": category,
            "headline": item.get("title", ""),
            "summary": item.get("summary_en", "") or item.get("summary", ""),
            "prelims": item.get("prelims_points", []),
            "relevance": item.get("relevance", 5),
            "timestamp": item.get("publishedAt", ""),
            "source": item.get("source", ""),
            "deep": {
                "prelims_points": item.get("prelims_points", []),
                "mains_angles": item.get("mains_angles", []),
                "interview_questions": item.get("interview_questions", [])
            }
        }
        
        grouped[category].append(formatted_item)
    
    return {
        "grouped": grouped,
        "total_items": len(notes_list),
        "categories": list(grouped.keys()),
        "timestamp": date
    }


@router.get("/docx/{date}")
def export_docx_get(
    date: str,
    lang: str = Query("en", description="Language: en, hi, or both"),
    x_api_key: Optional[str] = Header(None),
):
    """
    Export saved notes for a specific date to DOCX format (GET method).
    This is the endpoint used by Streamlit page 6.
    
    Args:
        date: Date string (YYYY-MM-DD)
        lang: Language for summary (en/hi/both)
        x_api_key: API key for authentication
    
    Returns:
        StreamingResponse with DOCX file
    """
    # Validate API key
    try:
        _validate_api_key(x_api_key)
    except HTTPException:
        # Skip auth if no API_KEY is set
        if os.getenv("API_KEY"):
            raise
    
    # Load saved notes
    notes = load_saved_notes()
    day_notes = notes.get(date)
    
    if not day_notes:
        logging.warning(f"No notes found for date: {date}")
        raise HTTPException(
            status_code=404,
            detail=f"No notes found for date: {date}"
        )
    
    # Handle list format (from saved_notes.json)
    if isinstance(day_notes, list):
        logging.info(f"Converting list format ({len(day_notes)} items) to structured format")
        
        structured = convert_list_to_structured_format(day_notes, date)
        
        try:
            bytes_data = build_docx_from_notes(
                structured,
                title=f"UPSC Notes - {date}"
            )
            logging.info(f"DOCX generated successfully, size: {len(bytes_data)} bytes")
        except Exception as e:
            logging.exception(f"Export to DOCX failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Export failed: {str(e)}"
            )
    
    # Handle dict format (legacy or single note)
    elif isinstance(day_notes, dict):
        logging.info(f"Using dict format for export")
        
        try:
            bytes_data = export_notes_to_docx(
                day_notes,
                cover=True,
                language=lang,
                cover_title=day_notes.get("title")
            )
            logging.info(f"DOCX generated successfully, size: {len(bytes_data)} bytes")
        except Exception as e:
            logging.exception(f"Export to DOCX failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Export failed: {str(e)}"
            )
    
    else:
        logging.error(f"Invalid notes structure for date {date}: {type(day_notes)}")
        raise HTTPException(
            status_code=500,
            detail=f"Invalid notes structure: {type(day_notes)}"
        )
    
    # Generate safe filename
    safe_name = f"UPSC_Notes_{date}"
    safe_name = "".join([c for c in safe_name if c.isalnum() or c in " _-."]).strip()
    safe_name = safe_name or f"notes_{date}"
    
    if not safe_name.lower().endswith(".docx"):
        safe_name = safe_name + ".docx"
    
    # Return as streaming response
    stream = io.BytesIO(bytes_data)
    headers = {
        "Content-Disposition": f"attachment; filename={safe_name}"
    }
    
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers
    )


@router.post("/docx")
def export_docx_post(
    date: str,
    language: str = "en",
    cover: bool = True,
    filename: Optional[str] = None,
    x_api_key: Optional[str] = Header(None),
):
    """
    Export saved notes for a specific date to DOCX format (POST method).
    Legacy endpoint for backward compatibility.
    
    Args:
        date: Date string (YYYY-MM-DD)
        language: Language for summary (en/hi)
        cover: Include cover page
        filename: Custom filename (optional)
        x_api_key: API key for authentication
    
    Returns:
        StreamingResponse with DOCX file
    """
    # Just redirect to GET method with same logic
    return export_docx_get(date, lang=language, x_api_key=x_api_key)


@router.get("/debug/{date}")
def debug_notes_structure(date: str):
    """
    Debug endpoint to check the structure of saved notes for a date.
    """
    notes = load_saved_notes()
    day_notes = notes.get(date)
    
    if not day_notes:
        return {"error": "No notes found for this date", "date": date}
    
    # Return structure info
    result = {
        "date": date,
        "type": str(type(day_notes)),
        "count": len(day_notes) if isinstance(day_notes, list) else 1
    }
    
    if isinstance(day_notes, list) and day_notes:
        result["first_item_keys"] = list(day_notes[0].keys())
        result["sample"] = day_notes[0]
    elif isinstance(day_notes, dict):
        result["keys"] = list(day_notes.keys())
        result["sample"] = {k: str(v)[:100] for k, v in list(day_notes.items())[:5]}
    
    return result