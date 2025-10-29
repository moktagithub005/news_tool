# utils/summaries.py
"""
Daily UPSC Summary Generator
- Creates daily news briefs from ingested content
- Saves structured summaries back into Chroma for revision
- Supports bilingual output (English + Hindi)
"""

from datetime import datetime
from typing import List
from langchain.schema import Document

from utils.rag_engine import build_rag_prompt
from utils.llm import get_llm


def generate_daily_summary(vs, language: str = "Both", top_k: int = 10) -> str:
    """
    Generate a high-level summary of the day's articles.
    Uses RAG to retrieve the key content and then summarize.
    """
    llm = get_llm()

    # Retrieve top chunks arbitrarily using '*' wildcard query
    docs = vs.similarity_search("India", k=top_k)
    context = [d.page_content for d in docs]

    prompt = f"""
You are a UPSC mentor. Create a daily current affairs summary from the content.
Include:
- 10 most important points of the day
- Key schemes/acts/policies
- International relations highlights
- Economy + Environment + Science updates
- UPSC exam relevance

Return output in this format:
[EN] English summary first
[HI] फिर वही सार हिंदी में भी दें

Content:
{''.join(context)}
"""

    result = llm.invoke(prompt)
    return result.content


def save_daily_summary(vs, summary_text: str, date_str: str, language: str):
    """
    Store daily summary inside ChromaDB for future RAG.
    """
    doc = Document(
        page_content=summary_text,
        metadata={
            "type": "daily_summary",
            "date": date_str,
            "lang": language,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    )
    vs.add_documents([doc])
    vs.persist()
    return True