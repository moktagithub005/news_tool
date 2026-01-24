"""
Analyzer wrapper - Uses REAL AI analysis
- Orchestrates PDF extraction → AI analysis → structured UPSC notes
- Produces same clean output as news ingestion
- Compatible with pdf_reader.py and pdf_analyzer.py
- Memory optimized for cloud deployment
"""

from typing import Dict, Any, List
import logging
import gc
from datetime import datetime

from utils.pdf_reader import extract_pdf_text_bytes
from utils.pdf_analyzer import analyze_pdf_text
from utils.config import UPSC_CATEGORIES

logger = logging.getLogger(__name__)


def analyze_pdf_and_build_notes(
    pdf_bytes: bytes,
    mode: str = "deep",
    deep_k: int = 5,
    enable_ocr: bool = True,
    min_relevance: float = 0.0,
) -> Dict[str, Any]:
    """
    End-to-end PDF analysis with REAL AI:
    - Extract text (OCR fallback)
    - Use LLM to analyze and categorize
    - Return structured UPSC notes (same format as news ingestion)

    Args:
        pdf_bytes: PDF file as bytes
        mode: Analysis mode ("deep" or "quick")
        deep_k: Number of top sections to analyze deeply
        enable_ocr: Whether to use OCR fallback for scanned PDFs
        min_relevance: Minimum relevance score for filtering (0-10)

    Returns:
        Dict with grouped items by category, matching news ingestion format
    """

    try:
        # 1. Extract text from PDF
        logger.info("Extracting text from PDF...")
        raw_text, num_pages, method = extract_pdf_text_bytes(
            pdf_bytes,
            enable_ocr=enable_ocr,
        )

        if not raw_text or len(raw_text.strip()) < 100:
            return {
                "ok": False,
                "error": "PDF contains insufficient readable text",
                "pages": num_pages,
                "method": method,
                "grouped": {},
                "total_items": 0,
                "categories": [],
            }

        logger.info(f"✅ Extracted {len(raw_text)} chars via {method} from {num_pages} pages")

        # 2. Use REAL AI analysis (from pdf_analyzer.py)
        logger.info("🧠 Running AI analysis...")
        
        # MEMORY OPTIMIZATION: Limit text size for analysis
        max_text_length = 100000  # ~100KB text limit for free tier
        if len(raw_text) > max_text_length:
            logger.warning(f"Text too long ({len(raw_text)} chars), truncating to {max_text_length}")
            raw_text = raw_text[:max_text_length]
        
        grouped_items, raw_responses = analyze_pdf_text(
            full_text=raw_text,
            language="Both",  # Support both English and Hindi
            chunk_size=4000,  # Smaller chunks for memory
            overlap=200,
            debug=False
        )
        
        # Clear memory after analysis
        del raw_text
        del raw_responses
        gc.collect()

        logger.info(f"✅ AI analysis complete. Generated items for {len([k for k,v in grouped_items.items() if v])} categories")

        # 3. Filter by min_relevance and add metadata
        filtered_grouped = {}
        total_items = 0
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        for category, items in grouped_items.items():
            if not items:
                continue
                
            # Filter by relevance
            filtered_items = [
                item for item in items 
                if int(item.get("relevance", 0)) >= min_relevance
            ]
            
            # Add metadata to each item
            for item in filtered_items:
                if "timestamp" not in item:
                    item["timestamp"] = timestamp
                if "source" not in item:
                    item["source"] = "PDF Document"
                    
                # Ensure all required fields exist
                item.setdefault("headline", item.get("title", ""))
                item.setdefault("summary", item.get("summary_en", ""))
                item.setdefault("prelims", item.get("prelims_points", []))
                
                # Build deep analysis structure
                item.setdefault("deep", {
                    "mains_angles": item.get("mains_angles", []),
                    "interview_questions": item.get("interview_questions", []),
                    "key_facts": item.get("key_facts", []),
                })
            
            if filtered_items:
                filtered_grouped[category] = filtered_items
                total_items += len(filtered_items)

        # 4. Return in the same format as news ingestion
        active_categories = [cat for cat, items in filtered_grouped.items() if items]
        
        return {
            "ok": True,
            "pages": num_pages,
            "method": method,
            "grouped": filtered_grouped,
            "total_items": total_items,
            "categories": active_categories,
            "timestamp": timestamp,
        }

    except Exception as e:
        logger.error(f"Error in analyze_pdf_and_build_notes: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e),
            "pages": 0,
            "method": "error",
            "grouped": {},
            "total_items": 0,
            "categories": [],
        }