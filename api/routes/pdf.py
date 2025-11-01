# api/routes/pdf.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
import traceback
import os

from utils.config import API_KEY as CONFIG_API_KEY
from utils.pdf_reader import analyze_pdf_bytes

router = APIRouter(prefix="/pdf", tags=["pdf"])

def _check_api_key(x_api_key: str):
    expected = os.getenv("API_KEY", CONFIG_API_KEY)
    return x_api_key == expected

@router.post("/analyze")
async def analyze_pdf(
    file: UploadFile = File(...),
    x_api_key: str | None = None,
    mode: str = "deep"
) -> Dict[str, Any]:
    """
    Upload a PDF, extract cleaned text, split into UPSC categories,
    and return structured notes.
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

        # Use the analyze_pdf_bytes function from pdf_reader.py
        # It handles everything: extraction, cleaning, sectioning, summarization
        result = analyze_pdf_bytes(raw_bytes, target_path=file.filename)
        
        # Add success flag and return
        result["ok"] = True
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")