

# =========================
# pages/3_🧱_Build_Index.py
# =========================

# NOTE: Save the following as pages/3_🧱_Build_Index.py


import os
from datetime import datetime
from typing import List
import streamlit as st

from langchain.schema import Document

from utils.vector_store import get_vectorstore, add_documents
from utils.pdf_reader import extract_text_from_pdf
from utils.config import UPLOAD_DIR

st.set_page_config(page_title="Build Index", page_icon="🧱", layout="wide")
st.title("🧱 Build / Update Index")

# Date box
def today_str():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")

date_str = st.text_input("Index Date (YYYY-MM-DD)", value=today_str())
chunk_size = st.slider("Chunk size", 600, 2000, 1200, 100)
overlap = st.slider("Overlap", 50, 400, 150, 10)

vs = get_vectorstore(date_str)

# Ingest categorized news
if st.button("🧠 Ingest Fetched News"):
    items = st.session_state.get("categorized_items", [])
    if not items:
        st.warning("No categorized items in session. Go to 'Ingest News' first.")
    else:
        docs: List[Document] = []
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        for it in items:
            block = (
                f"Title: {it.get('title','')}\n"
                f"Category: {it.get('category','')}\n"
                f"Tags: {', '.join(it.get('tags', []))}\n"
                f"Summary(EN): {it.get('summary_en','')}\n"
                f"Summary(HI): {it.get('summary_hi','')}\n"
                f"Prelims: {it.get('prelims_points','')}\n"
                f"Mains: {it.get('mains_angles','')}\n"
                f"Interview: {it.get('interview_questions','')}\n"
                f"Source: {it.get('source',{}).get('name','')} | URL: {it.get('url','')} | Published: {it.get('publishedAt','')}\n"
            )
            # Simple chunking by length
            for i in range(0, len(block), max(1, chunk_size - overlap)):
                chunk = block[i:i+chunk_size]
                docs.append(Document(page_content=chunk, metadata={
                    "source": it.get("source",{}).get("name",""),
                    "url": it.get("url",""),
                    "category": it.get("category",""),
                    "date": date_str,
                    "ingested_at": ts,
                }))
        added = add_documents(vs, docs)
        st.success(f"Added {added} chunks from fetched news to {date_str}.")

# Ingest PDFs
if st.button("📥 Ingest PDFs from uploads/"):
    pdfs = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith('.pdf')]
    if not pdfs:
        st.warning("No PDFs in uploads/")
    else:
        docs: List[Document] = []
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        for fname in pdfs:
            path = os.path.join(UPLOAD_DIR, fname)
            text = extract_text_from_pdf(path)
            for i in range(0, len(text), max(1, chunk_size - overlap)):
                chunk = text[i:i+chunk_size]
                docs.append(Document(page_content=chunk, metadata={
                    "source": fname,
                    "date": date_str,
                    "ingested_at": ts,
                }))
        added = add_documents(vs, docs)
        st.success(f"Added {added} chunks from PDFs to {date_str}.")

# Danger: clear index
if st.button("🗑️ Clear index for this date"):
    import shutil
    try:
        base = vs._persist_directory  # path used by Chroma
        shutil.rmtree(base)
        os.makedirs(base, exist_ok=True)
        st.success("Index cleared. (Restart retrieval cache if needed)")
    except Exception as e:
        st.error(str(e))


