# utils/analyzer_wrapper.py
"""
Wrapper to analyze PDF text and build structured notes for UPSC preparation.
Clean, concise output with short bullet points.
"""

from typing import Dict, List
from datetime import datetime
from utils.pdf_reader import split_into_sections, sentence_tokenize, tfidf_summarize
import re


def extract_key_headline(text: str) -> str:
    """
    Extract a clean, concise headline from text.
    Takes first meaningful sentence or creates one from key terms.
    """
    if not text or not text.strip():
        return ""
    
    sentences = sentence_tokenize(text)
    if not sentences:
        return text[:100] + "..." if len(text) > 100 else text
    
    # Get first substantial sentence
    for sent in sentences[:3]:
        # Clean sentence
        clean = sent.strip()
        # Remove common prefixes
        clean = re.sub(r'^(The|A|An)\s+', '', clean)
        # Prefer sentences between 50-200 chars
        if 50 <= len(clean) <= 200:
            return clean
    
    # Fallback to first sentence, truncated if needed
    first = sentences[0].strip()
    return first[:150] + "..." if len(first) > 150 else first


def create_short_summary(text: str, max_length: int = 200) -> str:
    """
    Create a very short, clean summary (1-2 sentences max).
    """
    if not text or not text.strip():
        return ""
    
    # Use TF-IDF to get most important sentences
    summary = tfidf_summarize(text, max_sentences=2)
    
    if not summary:
        sentences = sentence_tokenize(text)
        summary = ". ".join(sentences[:2]) if sentences else text[:max_length]
    
    # Clean up
    summary = summary.strip()
    
    # Ensure it ends properly
    if not summary.endswith(('.', '!', '?')):
        summary += "."
    
    # Truncate if too long
    if len(summary) > max_length:
        summary = summary[:max_length-3] + "..."
    
    return summary


def extract_prelims_points(text: str, max_points: int = 3) -> List[str]:
    """
    Extract short, factual prelims pointers (one-liners).
    """
    sentences = sentence_tokenize(text)
    if not sentences:
        return []
    
    points = []
    
    # Look for factual, informative sentences
    for sent in sentences:
        clean = sent.strip()
        
        # Skip if too short or too long
        if len(clean) < 30 or len(clean) > 120:
            continue
        
        # Skip questions
        if clean.endswith('?'):
            continue
        
        # Skip opinion/subjective statements
        if any(word in clean.lower() for word in ['should', 'must', 'ought', 'believe', 'think']):
            continue
        
        # Prefer sentences with numbers, names, dates, or key facts
        has_facts = bool(re.search(r'\d+|[A-Z][a-z]+\s+[A-Z][a-z]+', clean))
        
        if has_facts or len(points) < max_points:
            # Clean up the point
            clean = re.sub(r'^(Headline|Summary|News):\s*', '', clean, flags=re.IGNORECASE)
            points.append(clean)
            
            if len(points) >= max_points:
                break
    
    return points[:max_points]


def extract_mains_angles(text: str, category: str, max_angles: int = 2) -> List[str]:
    """
    Extract 2 concise mains analysis angles (one-liners).
    """
    angles = []
    
    # Category-specific angle templates
    angle_templates = {
        "polity": [
            "Explain implications for governance/public policy.",
            "Discuss potential impact on constitutional provisions."
        ],
        "economy": [
            "Discuss potential impact on economy and society.",
            "Analyze fiscal/monetary policy implications."
        ],
        "international": [
            "Analyze impact on India's foreign relations.",
            "Discuss geopolitical implications for the region."
        ],
        "environment": [
            "Assess environmental and sustainability implications.",
            "Discuss impact on climate goals and biodiversity."
        ],
        "science_tech": [
            "Discuss technological advancement and applications.",
            "Analyze implications for innovation and development."
        ],
        "social": [
            "Examine social impact and welfare implications.",
            "Discuss effects on equity and inclusiveness."
        ],
        "security": [
            "Analyze national security implications.",
            "Discuss strategic importance for defense."
        ],
        "geography": [
            "Examine geographical significance and regional impact.",
            "Discuss implications for resource management."
        ]
    }
    
    # Get category-specific angles or use general ones
    templates = angle_templates.get(category, [
        "Explain implications for governance/public policy.",
        "Discuss potential impact on economy and society."
    ])
    
    return templates[:max_angles]


def calculate_relevance(text: str, category: str) -> int:
    """
    Calculate relevance score (1-10) based on text content and category.
    """
    if not text or not text.strip():
        return 1
    
    word_count = len(text.split())
    
    # Base score on content quality
    if word_count < 30:
        score = 2
    elif word_count < 80:
        score = 5
    elif word_count < 200:
        score = 7
    else:
        score = 8
    
    # Boost for important categories
    important_cats = ["polity", "economy", "international", "environment"]
    if category in important_cats:
        score = min(10, score + 2)
    
    # Boost if contains key UPSC terms
    upsc_keywords = ['policy', 'governance', 'constitution', 'act', 'scheme', 
                     'government', 'india', 'minister', 'court', 'reform']
    text_lower = text.lower()
    keyword_count = sum(1 for kw in upsc_keywords if kw in text_lower)
    
    if keyword_count >= 3:
        score = min(10, score + 1)
    
    return max(1, min(10, score))


def analyze_pdf_and_build_notes(
    full_text: str,
    deep_k: int = 5,
    min_relevance: int = 4
) -> Dict:
    """
    Analyze PDF text and build clean, structured notes with short points.
    
    Args:
        full_text: The complete PDF text
        deep_k: Number of items to do deep analysis on
        min_relevance: Minimum relevance score to include
    
    Returns:
        Dict with structured notes grouped by category
    """
    # Split into sections
    sections = split_into_sections(full_text)
    
    grouped = {}
    all_items = []
    
    for category, section_text in sections.items():
        if not section_text or len(section_text.strip()) < 50:
            continue
        
        # Create headline
        headline = extract_key_headline(section_text)
        if not headline:
            continue
        
        # Create short summary
        summary = create_short_summary(section_text, max_length=180)
        
        # Calculate relevance
        relevance = calculate_relevance(section_text, category)
        
        # Skip if below minimum relevance
        if relevance < min_relevance:
            continue
        
        # Extract clean points
        prelims = extract_prelims_points(section_text, max_points=3)
        mains = extract_mains_angles(section_text, category, max_angles=2)
        
        item = {
            "category": category,
            "headline": headline,
            "summary": summary,
            "prelims": prelims,
            "relevance": relevance,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": "PDF Document",
            "deep": {
                "prelims_points": prelims,
                "mains_angles": mains,
                "interview_questions": []
            }
        }
        
        # Group by category
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(item)
        all_items.append(item)
    
    # Sort items by relevance
    all_items.sort(key=lambda x: x["relevance"], reverse=True)
    
    # Mark top items for deep analysis
    for i, item in enumerate(all_items[:deep_k]):
        item["has_deep_analysis"] = True
    
    return {
        "grouped": grouped,
        "total_items": len(all_items),
        "categories": list(grouped.keys()),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }