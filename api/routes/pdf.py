from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from utils.pdf_reader import extract_pdf_text_bytes, split_into_sections, summarize_sections_groq

router = APIRouter(prefix="/pdf")

@router.post("/analyze")
async def analyze_pdf(file: UploadFile = File(...), mode: str = "deep"):
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File read failed: {e}")

    try:
        text = extract_pdf_text_bytes(content)
        if not text or len(text.strip()) < 100:
            return JSONResponse(
                {"ok": False, "message": "No readable text found. (Try OCR or higher-quality scan)", "count": 0, "items": []},
                status_code=200,
            )

        sections = split_into_sections(text)
        summaries = summarize_sections_groq(sections, mode=mode)

        return {
            "ok": True,
            "count": len(summaries),
            "items": summaries,
            "message": f"Extracted {len(sections)} sections after cleaning."
        }

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
