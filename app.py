import streamlit as st
from utils.config import LANGSMITH_API_KEY, LANGCHAIN_PROJECT, VECTOR_DIR, UPLOAD_DIR

st.set_page_config(
    page_title="UNISOLE UPSC AI News",
    page_icon="📰",
    layout="wide",
)

st.title("UNISOLE UPSC AI News")
st.caption("Daily Current Affairs for UPSC Prelims & Mains – Simplified")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("LangSmith Tracing", "On" if bool(LANGSMITH_API_KEY) else "Off")
    st.metric("Project", LANGCHAIN_PROJECT)
with col2:
    st.metric("Vector Store Base", VECTOR_DIR)
    st.metric("Uploads Folder", UPLOAD_DIR)
with col3:
    st.info("Navigate using the sidebar →")

st.divider()

st.subheader("How to use this tool")
st.markdown("""
1. **📥 Ingest News** – Fetch daily news (NewsAPI + PIB + PRS) and categorize it.
2. **📄 Upload PDFs** – Add newspaper PDFs like *The Hindu* or *Indian Express*.
3. **🧱 Build Index** – Store news/PDFs into vector database (per date).
4. **💬 Ask Questions** – Query news using AI RAG (English/Hindi/Both).
5. **📰 Daily Summary** – Generate UPSC-style daily revision notes.
""")

st.success("Tip: Use one index per day for clear revision. Example: 2025-01-18")
st.info("Go to **📥 Ingest News** in the sidebar to continue.")
