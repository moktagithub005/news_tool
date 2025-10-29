# api/routes/rag.py
from fastapi import APIRouter, Depends
from api.deps import verify_api_key
from api.schemas import RAGQueryRequest, RAGQueryResponse
from utils.vector_store import get_vectorstore
from utils.llm import get_llm

router = APIRouter(prefix="/rag", tags=["rag"])

@router.post("/query", response_model=RAGQueryResponse)
def rag_query(req: RAGQueryRequest, _: bool = Depends(verify_api_key)):
    vs = get_vectorstore(req.index_date)
    retriever = vs.as_retriever(search_kwargs={"k": req.k})
    llm = get_llm()
    docs = retriever.get_relevant_documents(req.question)
    context = "\n\n".join(d.page_content for d in docs)
    prompt = f"Use the context to answer concisely for UPSC:\n\nContext:\n{context}\n\nQuestion: {req.question}\n\nAnswer:"
    answer = llm.invoke(prompt).content
    sources = [{"metadata": d.metadata} for d in docs]
    return RAGQueryResponse(answer=answer, sources=sources)
