# pages/1_Ingest_News.py
# Streamlit Ingest Page -> FastAPI backend
# - Quick query buttons (horizontal)
# - Full controls (query/days/page size/sources/AI mode)
# - English-only summaries on cards
# - Save to Notes via /notes/save
# - Clean Blue/White card UI

import streamlit as st
from datetime import datetime
from typing import Dict, List

from utils.api_client import post  # uses API_BASE_URL + API_KEY from .env

st.set_page_config(page_title="Ingest News", page_icon="📥", layout="wide")
st.title("📥 Ingest News")
st.caption("Fetch UPSC-relevant items via FastAPI, auto-categorized & ranked by AI relevance.")

# --------- Styling (Blue/White cards) ----------
CARD_CSS = """
<style>
.upsc-card {
  background:#fff; border:1px solid #e6eef8; border-left:5px solid #1f6feb;
  border-radius:12px; padding:16px 18px; margin-bottom:14px;
  box-shadow:0 1px 3px rgba(31,111,235,0.06);
}
.upsc-card h4 { margin: 4px 0 6px 0; }
.badge {
  display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px;
  background:#eaf2ff; color:#1f6feb; border:1px solid #cfe0ff; margin-right:6px;
}
.meta { color:#6b7785; font-size:13px; margin-bottom:6px; }
.section-title { font-weight:600; margin-top:8px; margin-bottom:4px; }
.sep { height:1px; background:#eef3fb; margin:10px 0; }
</style>
"""
st.markdown(CARD_CSS, unsafe_allow_html=True)

# --------- Helpers ----------
def clean_bullets(bullets: List[str]) -> List[str]:
    cleaned = []
    for b in bullets or []:
        if not b:
            continue
        t = str(b).strip("-• ").strip()
        if len(t) < 3:
            continue
        if t.lower() in {"and","or","the","of","in","to"}:
            continue
        if not any(c.isalpha() for c in t):
            continue
        cleaned.append(t)
    return cleaned

def api_ingest(query: str, days_back: int, page_size: int,
               use_newsapi: bool, use_pib: bool, use_prs: bool,
               ai_mode: str) -> Dict:
    payload = {
        "query": query,
        "days_back": days_back,
        "use_newsapi": use_newsapi,
        "use_pib": use_pib,
        "use_prs": use_prs,
        "page_size": page_size,
        "ai_mode": "deep" if ai_mode.lower() == "deep" else "fast",
    }
    return post("/ingest/news", json=payload)

def api_save_note(date_str: str, item: Dict) -> Dict:
    # backend expects SaveNoteRequest (same fields as IngestItem + date)
    body = {
        "date": date_str,
        "title": item.get("title",""),
        "url": item.get("url"),
        "publishedAt": item.get("publishedAt"),
        "source": item.get("source"),
        "category": item.get("category","general"),
        "relevance": int(item.get("relevance", 0)),
        "summary_en": item.get("summary_en",""),
        "summary_hi": "",  # English only on cards; backend can still store empty
        "prelims_points": item.get("prelims_points",[]),
        "mains_angles": item.get("mains_angles",[]),
        "interview_questions": item.get("interview_questions",[]),
        "schemes_acts_policies": item.get("schemes_acts_policies",[]),
        "institutions": item.get("institutions",[]),
        "dates": item.get("dates",[])
    }
    return post("/notes/save", json=body)

# --------- Controls ----------
c1, c2 = st.columns([3,2])
with c1:
    query = st.text_input(
        "News query (India focused)",
        value="India AND (Supreme Court OR RBI OR government policy OR bill OR scheme OR ISRO OR environment)"
    )
    days_back = st.slider("Days back", 1, 7, 2)
with c2:
    page_size = st.slider("Max items to fetch", 10, 50, 20, 5)
    notes_date = st.text_input("Notes Date (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))

s1, s2, s3, s4, s5 = st.columns([1,1,1,2,2])
with s1:
    use_newsapi = st.checkbox("NewsAPI", value=True)
with s2:
    use_pib = st.checkbox("PIB", value=True)
with s3:
    use_prs = st.checkbox("PRS", value=True)
with s4:
    ai_mode = st.radio("AI Relevance", options=["Fast","Deep"], index=1, horizontal=True)
with s5:
    st.write("")  # spacer
    fetch_now = st.button("🔄 Fetch & Rank", type="primary")

# --------- Quick Query Buttons (row) ----------
st.markdown("**Quick Queries:**")
qb1, qb2, qb3, qb4, qb5, qb6, qb7, qb8 = st.columns(8)
with qb1:
    if st.button("🏛 Polity"):
        query = "India AND (parliament OR bill OR act OR constitution OR supreme court)"
with qb2:
    if st.button("💰 Economy"):
        query = "India AND (GDP OR inflation OR RBI OR budget OR fiscal OR repo)"
with qb3:
    if st.button("🌍 IR"):
        query = "India AND (foreign policy OR UN OR G20 OR FTA OR Indo-Pacific)"
with qb4:
    if st.button("🔬 Sci-Tech"):
        query = "India AND (ISRO OR DRDO OR AI OR quantum OR semiconductor)"
with qb5:
    if st.button("🌱 Environment"):
        query = "India AND (climate OR biodiversity OR wildlife OR pollution OR cyclone)"
with qb6:
    if st.button("📜 Schemes"):
        query = "India AND (scheme OR yojana OR mission OR policy OR guidelines)"
with qb7:
    if st.button("⚖ Judiciary"):
        query = "India AND (Supreme Court OR High Court OR constitutional bench OR verdict)"
with qb8:
    if st.button("🏗 Governance"):
        query = "India AND (NITI Aayog OR e-governance OR digital public infrastructure OR regulation)"

st.divider()

# --------- Fetch via API ----------
if fetch_now:
    try:
        with st.spinner("Contacting backend and ranking items by UPSC relevance..."):
            data = api_ingest(
                query=query,
                days_back=days_back,
                page_size=page_size,
                use_newsapi=use_newsapi,
                use_pib=use_pib,
                use_prs=use_prs,
                ai_mode=ai_mode,
            )
        items = data.get("items", [])
        st.session_state["ingested_items"] = items
        st.success(f"Fetched {len(items)} ranked items.")
    except Exception as e:
        st.error(f"Backend API not reachable or failed: {e}")

items: List[Dict] = st.session_state.get("ingested_items", [])

# --------- Render cards ----------
if items:
    st.subheader("🧾 UPSC Cards (Sorted by AI Relevance)")
    for idx, it in enumerate(items, start=1):
        cat = (it.get("category","general") or "general").replace("_"," ").title()
        rel = int(it.get("relevance", 0))
        title = it.get("title","(No title)")
        source = it.get("source","")
        published = it.get("publishedAt","")
        url = it.get("url","") or ""

        st.markdown(f"""
<div class="upsc-card">
  <div>
    <span class="badge">{cat}</span>
    <span class="badge">⭐ Relevance: {rel}/10</span>
  </div>
  <h4>📰 {title}</h4>
  <div class="meta">
    {'📅 ' + published if published else ''} {' • 🔗 ' + source if source else ''} {(' • <a href="'+url+'" target="_blank">Read full</a>') if url else ''}
  </div>
  <div class="sep"></div>
""", unsafe_allow_html=True)

        # English-only summaries on cards
        if it.get("summary_en"):
            st.markdown("**✅ Summary (English):**")
            st.write(it["summary_en"])

        # Prelims / Mains (cleaned bullets)
        prelims = clean_bullets(it.get("prelims_points", []))
        mains = clean_bullets(it.get("mains_angles", []))
        if prelims:
            st.markdown("**📌 Prelims Pointers:**")
            st.markdown("- " + "\n- ".join(prelims))
        if mains:
            st.markdown("**📝 Mains Analysis:**")
            st.markdown("- " + "\n- ".join(mains))

        # Tail bits
        tail_bits = []
        if it.get("schemes_acts_policies"):
            tail_bits.append("**Schemes/Acts/Policies:** " + ", ".join(it["schemes_acts_policies"]))
        if it.get("institutions"):
            tail_bits.append("**Institutions:** " + ", ".join(it["institutions"]))
        if it.get("dates"):
            tail_bits.append("**Dates:** " + ", ".join(it["dates"]))
        if tail_bits:
            st.markdown("<div class='sep'></div>", unsafe_allow_html=True)
            st.markdown("  \n".join(tail_bits))

        # Actions row
        c1, c2, c3 = st.columns([1,1,6])
        if c1.button("⭐ Save to Notes", key=f"save_{idx}"):
            try:
                resp = api_save_note(notes_date, it)
                msg = resp["message"] if isinstance(resp, dict) and "message" in resp else "Saved."
                st.success(msg)
            except Exception as e:
                st.error(f"Save failed: {e}")
        if c2.button("📋 Copy Title", key=f"copy_{idx}"):
            st.code(title)

        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Use a quick query or enter your own, then click **Fetch & Rank**.")
