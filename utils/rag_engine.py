# utils/rag_engine.py
"""
RAG Engine for UPSC QA
- Retrieves context from ChromaDB
- Builds UPSC-specific bilingual prompt
- Uses Groq LLM to generate final answer
"""

from typing import List
from langchain.schema import Document
from langchain_core.messages import SystemMessage, HumanMessage

from utils.llm import get_llm


def build_rag_prompt(question: str, context_chunks: List[str], language: str) -> str:
    """
    Builds bilingual UPSC prompt based on selected language.
    """
    context_text = "\n\n".join(
        [f"[Source {i+1}]\n{c}" for i, c in enumerate(context_chunks)]
    )

    if language.lower() == "hindi":
        return f"""
आप UPSC मेंस/प्री परीक्षा के लिए करंट अफेयर्स विशेषज्ञ हैं।
नीचे दिया गया संदर्भ पढ़कर प्रश्न का तथ्यात्मक और सिलेबस-लिंक्ड उत्तर दें।

संदर्भ:
{context_text}

प्रश्न:
{question}

उत्तर संरचना:
- प्रमुख तथ्य व डेटा
- संबंधित कानून/नीतियाँ/संस्थाएँ
- पृष्ठभूमि व विश्लेषण
- प्रीलिम्स तथ्य
- मेंस उत्तर दृष्टिकोण
        """

    if language.lower() == "both":
        return f"""
You are a UPSC current affairs mentor. Use the below context to answer the question.

Context:
{context_text}

Question:
{question}

Answer in two sections:
[EN] Key facts, acts/policies, prelims points, mains analysis, interview angle.
[HI] उपरोक्त का संक्षिप्त हिंदी संस्करण भी दें।
        """

    # Default = English
    return f"""
You are a UPSC current affairs expert.
Use only the context below to answer the question clearly.

Context:
{context_text}

Question:
{question}

Answer structure:
- Key facts
- Relevant Acts/Policies
- Background analysis
- Prelims facts
- Mains answer style
    """


def answer_with_rag(vs, query: str, language: str, k: int = 5):
    """
    Main RAG function.
    - Search vector DB
    - Build prompt
    - Run LLM
    """
    llm = get_llm()
    results: List[Document] = vs.similarity_search(query, k=k)
    context = [doc.page_content for doc in results]

    prompt = build_rag_prompt(query, context, language)

    system_message = SystemMessage(content="You are a precise UPSC mentor. Answer from the context only.")
    human_message = HumanMessage(content=prompt)

    response = llm.invoke([system_message, human_message])

    return response.content, results
