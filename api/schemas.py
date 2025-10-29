# api/schemas.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class IngestRequest(BaseModel):
    query: str
    days_back: int = 2
    use_newsapi: bool = True
    use_pib: bool = True
    use_prs: bool = True
    page_size: int = 20
    ai_mode: str = Field("deep", pattern="^(fast|deep)$")


class IngestItem(BaseModel):
    title: str
    url: Optional[str] = None
    publishedAt: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = "general"
    relevance: int = 0
    summary_en: Optional[str] = None
    summary_hi: Optional[str] = None
    prelims_points: Optional[List[str]] = None
    mains_angles: Optional[List[str]] = None
    interview_questions: Optional[List[str]] = None
    schemes_acts_policies: Optional[List[str]] = None
    institutions: Optional[List[str]] = None
    dates: Optional[List[str]] = None

class IngestResponse(BaseModel):
    count: int
    items: List[IngestItem]

class SaveNoteRequest(IngestItem):
    date: str

class NotesListResponse(BaseModel):
    date: str
    items: List[IngestItem]

class PDFAnalyzeRequest(BaseModel):
    index_date: str
    include_hi: bool = False

class PDFAnalyzeResponse(BaseModel):
    date: str
    counts_by_category: Dict[str, int]
    # optional: you can add export urls or ids

class RAGQueryRequest(BaseModel):
    index_date: str
    question: str
    k: int = 4

class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = []
