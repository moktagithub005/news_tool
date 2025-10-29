
# =========================
# pages/4_💬_Ask_Questions.py
# =========================

# NOTE: Save the following as pages/4_💬_Ask_Questions.py


import streamlit as st
from utils.vector_store import get_vectorstore
from utils.rag_engine import answer_with_rag

st.set_page_config(page_title="Ask Questions", page_icon="💬", layout="wide")
st.title("💬 Ask UPSC Questions (RAG)")

# Controls

def today_str():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")

date_str = st.text_input("Index Date (YYYY-MM-DD)", value=today_str())
language = st.radio("Answer Language", ["English", "Hindi", "Both"], index=2, horizontal=True)
query = st.text_input("Your question", placeholder="e.g., List new schemes and their ministries mentioned today")
top_k = st.slider("Retrieve top-k", 2, 12, 6)

if st.button("🔎 Search & Answer", type="primary") and query:
    vs = get_vectorstore(date_str)
    with st.spinner("Retrieving & thinking..."):
        answer, results = answer_with_rag(vs, query, language, k=top_k)
    st.markdown("### 📌 Answer")
    st.write(answer)

    with st.expander("Show retrieved chunks"):
        for i, r in enumerate(results):
            src = r.metadata.get('source')
            st.markdown(f"**Source {i+1}:** `{src}`")
            st.write(r.page_content[:800] + ("..." if len(r.page_content) > 800 else ""))

