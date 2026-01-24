"""
Enhanced PDF Reader with conditional OCR.
- Uses fitz (PyMuPDF) or PyPDF2 for text extraction
- Falls back to OCR (pdf2image + pytesseract) if text < 100 chars total
- Excludes image-only pages and junk text
- Splits into UPSC-ready sections
"""

from typing import List, Dict, Any
import io
import os
import logging
import re
import warnings

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    from pdf2image import convert_from_bytes
    import pytesseract
    from PIL import Image
    # Increase the decompression bomb limit for large PDFs
    Image.MAX_IMAGE_PIXELS = None  # Disable limit entirely
    # Or set a higher limit: Image.MAX_IMAGE_PIXELS = 200000000
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


# ---------- Helper functions ----------

def _normalize_text(text: str) -> str:
    """Clean and normalize extracted text."""
    if not text:
        return ""
    text = text.replace("\x00", "").replace("\r", " ").strip()
    return " ".join(text.split())


def sentence_tokenize(text: str) -> List[str]:
    """
    Simple sentence tokenizer using regex.
    Splits on periods, exclamation marks, and question marks followed by whitespace.
    """
    if not text:
        return []
    
    # Split on sentence-ending punctuation followed by space or end of string
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Clean up and filter out empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences


def tfidf_summarize(text: str, num_sentences: int = 5) -> str:
    """
    Simple TF-IDF based summarization.
    Extracts the most important sentences based on word frequency.
    """
    if not text or not text.strip():
        return ""
    
    sentences = sentence_tokenize(text)
    
    if len(sentences) <= num_sentences:
        return text
    
    # Calculate word frequencies (simple TF)
    words = re.findall(r'\b\w+\b', text.lower())
    word_freq = {}
    for word in words:
        if len(word) > 3:  # Ignore very short words
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Score each sentence based on word frequencies
    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        sentence_words = re.findall(r'\b\w+\b', sentence.lower())
        score = sum(word_freq.get(word, 0) for word in sentence_words if len(word) > 3)
        if score > 0:
            sentence_scores[i] = score / len(sentence_words)  # Normalize by length
    
    # Get top sentences
    top_indices = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:num_sentences]
    top_indices.sort()  # Maintain original order
    
    summary = " ".join(sentences[i] for i in top_indices)
    return summary


# ---------- Extraction Methods ----------

def extract_with_fitz(pdf_bytes: bytes) -> str:
    """Extract text with PyMuPDF."""
    if not HAS_FITZ:
        raise RuntimeError("PyMuPDF not installed")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page in doc:
        txt = page.get_text("text") or ""
        pages.append(_normalize_text(txt))
    doc.close()
    return "\n".join(pages)


def extract_with_pypdf2(pdf_bytes: bytes) -> str:
    """Extract text with PyPDF2."""
    if not HAS_PYPDF2:
        raise RuntimeError("PyPDF2 not installed")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    texts = []
    for page in reader.pages:
        t = page.extract_text() or ""
        texts.append(_normalize_text(t))
    return "\n".join(texts)


def extract_with_ocr(pdf_bytes: bytes, dpi: int = 150) -> str:
    """OCR fallback: Convert PDF pages to images and run Tesseract OCR."""
    if not HAS_OCR:
        raise RuntimeError("OCR dependencies not installed (pdf2image, pytesseract, Pillow)")
    
    # MEMORY OPTIMIZATION: Process one page at a time instead of all at once
    import gc
    
    # Get page count first without loading all pages
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        num_pages = len(doc)
        doc.close()
    except:
        num_pages = 10  # fallback estimate
    
    texts = []
    
    # Process pages in small batches to reduce memory
    batch_size = 2  # Process 2 pages at a time
    for start_page in range(0, min(num_pages, 20), batch_size):  # Limit to 20 pages max
        try:
            # Convert only current batch
            pages = convert_from_bytes(
                pdf_bytes, 
                dpi=dpi,
                first_page=start_page + 1,
                last_page=min(start_page + batch_size, num_pages)
            )
            
            for idx, img in enumerate(pages):
                try:
                    # Resize image to reduce memory before OCR
                    max_size = (1600, 1600)  # Limit image size
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    text = pytesseract.image_to_string(img, lang="eng")
                    text = _normalize_text(text)
                    if len(text) > 100:
                        texts.append(text)
                    
                    # Clear image from memory
                    del img
                except Exception as e:
                    logger.warning(f"OCR failed on page {start_page + idx}: {e}")
            
            # Clear batch from memory
            del pages
            gc.collect()
            
        except Exception as e:
            logger.warning(f"Failed to process batch starting at page {start_page}: {e}")
            continue
    
    return "\n".join(texts)


# ---------- Unified entry point ----------

def extract_pdf_text_bytes(pdf_bytes, enable_ocr: bool = True):
    """
    Main entry: extract text; fallback to OCR if too short.
    Accepts: bytes, bytearray, file path (str), file-like object, or already-extracted text
    Returns: (raw_text, num_pages, method_used)
    """
    # Normalize input to bytes
    if isinstance(pdf_bytes, str):
        # Check if it's already extracted text (contains actual content, not a file path)
        # File paths are usually short and don't contain special characters like Hindi text
        if len(pdf_bytes) > 200 or (len(pdf_bytes) > 50 and not pdf_bytes.endswith('.pdf')):
            # This looks like already-extracted text, not a file path
            logger.info("Input appears to be already-extracted text, returning as-is")
            # Estimate pages (rough guess: 3000 chars per page)
            estimated_pages = max(1, len(pdf_bytes) // 3000)
            return pdf_bytes, estimated_pages, "pre-extracted"
        
        # It's a file path
        import os
        if os.path.exists(pdf_bytes):
            with open(pdf_bytes, 'rb') as f:
                pdf_bytes = f.read()
        else:
            # Last check: maybe it's short extracted text that looks like a path
            logger.warning(f"String input is not a valid file path, treating as extracted text")
            estimated_pages = max(1, len(pdf_bytes) // 3000)
            return pdf_bytes, estimated_pages, "pre-extracted"
            
    elif isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)
    elif hasattr(pdf_bytes, 'read'):
        # File-like object
        content = pdf_bytes.read()
        if isinstance(content, str):
            # File object returned string (already extracted text)
            estimated_pages = max(1, len(content) // 3000)
            return content, estimated_pages, "pre-extracted"
        pdf_bytes = bytes(content) if isinstance(content, bytearray) else content
    elif not isinstance(pdf_bytes, bytes):
        raise TypeError(f"Expected bytes, str (filepath), or file-like object, got {type(pdf_bytes)}")
    
    text = ""
    num_pages = 0
    method = "none"

    # 1. Try fitz first (best)
    if HAS_FITZ:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            num_pages = len(doc)
            pages = []
            for page in doc:
                txt = page.get_text("text") or ""
                pages.append(_normalize_text(txt))
            doc.close()
            text = "\n".join(pages)
            method = "fitz"
        except Exception as e:
            logger.warning(f"fitz failed: {e}")

    # 2. Fallback to PyPDF2
    if not text or len(text.strip()) < 100:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            num_pages = len(reader.pages)
            texts = []
            for page in reader.pages:
                t = page.extract_text() or ""
                texts.append(_normalize_text(t))
            text = "\n".join(texts)
            method = "pypdf2"
        except Exception as e:
            logger.warning(f"PyPDF2 failed: {e}")

    # 3. OCR fallback (only if text is too short and OCR is enabled)
    if enable_ocr and len(text.strip()) < 100 and HAS_OCR:
        logger.info("Text content too short — running OCR fallback...")
        try:
            # Suppress PIL decompression bomb warnings for large PDFs
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)
                # Use lower DPI (150 instead of 200) to reduce memory
                text = extract_with_ocr(pdf_bytes, dpi=150)
                method = "ocr"
        except Exception as e:
            logger.error(f"OCR failed: {e}")

    return text, num_pages, method


# ---------- Section splitting ----------

def validate_sections(sections: Any) -> List[Dict[str, Any]]:
    """Ensure sections is a list of dicts, not a single dict or other type."""
    if not sections:
        return []
    
    # If it's a single dict, wrap it in a list
    if isinstance(sections, dict):
        return [sections]
    
    # If it's a list, ensure each item is a dict
    if isinstance(sections, list):
        validated = []
        for item in sections:
            if isinstance(item, dict):
                validated.append(item)
            elif isinstance(item, str):
                # Convert string to dict format
                validated.append({"title": "", "text": item, "index": len(validated)})
        return validated
    
    return []


def split_into_sections(raw_text: str, min_chars: int = 100) -> List[Dict[str, Any]]:
    """Split into sections and remove junk under 100 chars."""
    if not raw_text or not raw_text.strip():
        return []

    # Split roughly by 2–3K characters
    chunk_size = 3000
    overlap = 200
    text = raw_text.strip()
    sections = []

    start = 0
    idx = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if len(chunk) >= min_chars:
            sections.append({
                "title": f"Section {idx + 1}",
                "text": chunk,
                "index": idx
            })
            idx += 1
        start = end - overlap

    # If no sections were created, create at least one
    if not sections and len(text) >= min_chars:
        sections.append({
            "title": "Section 1",
            "text": text,
            "index": 0
        })

    return sections


# ---------- Backward compatibility aliases ----------

def extract_text_from_pdf(pdf_source, enable_ocr: bool = True) -> str:
    """
    Backward compatibility wrapper for extract_pdf_text_bytes.
    Returns only the text (not num_pages or method).
    
    Args:
        pdf_source: PDF as bytes, file path, or file-like object
        enable_ocr: Whether to use OCR fallback
        
    Returns:
        Extracted text as string
    """
    text, num_pages, method = extract_pdf_text_bytes(pdf_source, enable_ocr=enable_ocr)
    return text
    """
    Dummy summarizer (replace with LLM call later).
    Handles both list of dicts and single dict inputs.
    """
    # Validate and normalize input
    if not sections:
        return []
    
    # Handle case where sections is a single dict
    if isinstance(sections, dict):
        sections = [sections]
    
    # Handle case where sections is not iterable
    if not isinstance(sections, (list, tuple)):
        logger.error(f"Invalid sections type: {type(sections)}")
        return []
    
    output = []
    for idx, s in enumerate(sections):
        # Skip non-dict items
        if not isinstance(s, dict):
            logger.warning(f"Section {idx} is not a dict (type: {type(s)}), skipping")
            continue
        
        # Extract text safely
        txt = s.get("text", "")
        if not txt:
            logger.warning(f"Section {idx} has no text, skipping")
            continue
            
        title = s.get("title", f"Section {idx + 1}")
        
        # Create summary
        summary = txt[:300] + "..." if len(txt) > 300 else txt
        
        output.append({
            "title": title,
            "summary": summary,
            "text": txt,  # Keep original text
            "length": len(txt),
            "index": s.get("index", idx)
        })
    
    return output