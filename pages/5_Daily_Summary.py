# =========================
# pages/5_📰_Daily_Summary.py
# =========================

# NOTE: Save the following as pages/5_📰_Daily_Summary.py


import streamlit as st
from utils.vector_store import get_vectorstore
from utils.summaries import generate_daily_summary, save_daily_summary

st.set_page_config(page_title="Daily Summary", page_icon="📰", layout="wide")
st.title("📰 Daily Summary (Bilingual)")

# Controls

def today_str():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")

date_str = st.text_input("Index Date (YYYY-MM-DD)", value=today_str())
language = st.radio("Summary Language", ["English", "Hindi", "Both"], index=2, horizontal=True)

if st.button("🧠 Generate Summary", type="primary"):
    vs = get_vectorstore(date_str)
    with st.spinner("Compiling the day in brief..."):
        summary = generate_daily_summary(vs, language=language, top_k=12)
    st.markdown("### 📌 Summary")
    st.write(summary)
    st.session_state["last_summary_text"] = summary

if st.button("💾 Save Summary to DB"):
    if not st.session_state.get("last_summary_text"):
        st.warning("Please generate a summary first.")
    else:
        vs = get_vectorstore(date_str)
        ok = save_daily_summary(vs, st.session_state["last_summary_text"], date_str, language)
        if ok:
            st.success("Saved into Chroma for future retrieval.")
