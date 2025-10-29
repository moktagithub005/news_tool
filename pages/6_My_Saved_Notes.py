# pages/6_My_Saved_Notes.py
# API-only Saved Notes: list, filter, paginate, delete (day/single), export DOCX

import streamlit as st
from typing import Dict, List, Any
from utils.api_client import get, post, delete

st.set_page_config(page_title="My Saved Notes", page_icon="📚", layout="wide")
st.title("📚 My Saved Notes")
st.caption("Review, filter, export, or delete your saved UPSC notes (via FastAPI backend).")

# ---------- Card CSS ----------
CARD_CSS = """
<style>
.upsc-card { background:#fff; border:1px solid #e6eef8; border-left:5px solid #1f6feb;
  border-radius:12px; padding:16px 18px; margin-bottom:14px; box-shadow:0 1px 3px rgba(31,111,235,0.06);}
.upsc-card h4 { margin:4px 0 6px 0;}
.badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px;
  background:#eaf2ff; color:#1f6feb; border:1px solid #cfe0ff; margin-right:6px;}
.meta { color:#6b7785; font-size:13px; margin-bottom:6px;}
.sep { height:1px; background:#eef3fb; margin:10px 0;}
.smallmuted { color:#8a97a6; font-size:12px;}
.pagination { color:#6b7785; font-size:13px;}
</style>
"""
st.markdown(CARD_CSS, unsafe_allow_html=True)

# ---------- Helpers ----------
def clean_bullets(bullets: List[str]) -> List[str]:
    out = []
    for b in bullets or []:
        if not b: continue
        t = str(b).strip("-• ").strip()
        if len(t) < 3: continue
        if t.lower() in {"and","or","the","of","in","to"}: continue
        if not any(c.isalpha() for c in t): continue
        out.append(t)
    return out

def api_list_notes(date_str: str) -> List[Dict[str, Any]]:
    resp = get(f"/notes/list/{date_str}")
    return resp.get("items", [])

def api_delete_day(date_str: str):
    return delete(f"/notes/delete/{date_str}")

def api_delete_one(date_str: str, title: str = None, url: str = None):
    payload = {"date": date_str}
    if title: payload["title"] = title
    if url: payload["url"] = url
    return post("/notes/delete_one", json=payload)

def api_export_docx(date_str: str, lang: str = "en") -> bytes:
    # Returns raw bytes (StreamingResponse) — our client returns .content
    return get(f"/export/docx/{date_str}", params={"lang": lang})

# ---------- Controls ----------
col_date, col_cat, col_lang, col_actions = st.columns([2,2,1,3])
with col_date:
    selected_date = st.text_input("Select Date (YYYY-MM-DD)", value=st.session_state.get("msn_date",""))
with col_cat:
    category_filter = st.selectbox(
        "Filter by Category",
        ["All","Polity","Economy","International","Environment","Science_Tech","Social","Security","Geography","Governance","general"],
        index=0
    )
with col_lang:
    export_lang = st.selectbox("DOCX Language", ["en","hi","both"], index=0)

# Actions: Refresh + Delete Day + Export
a1, a2, a3 = col_actions.columns(3)
with a1:
    if st.button("🔄 Refresh Notes", type="secondary"):
        st.session_state["msn_refresh"] = True
with a2:
    if st.button("🗑️ Delete ALL (this date)"):
        if selected_date:
            try:
                api_delete_day(selected_date)
                st.success(f"Deleted all notes for {selected_date}.")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")
        else:
            st.warning("Enter a date first.")
with a3:
    if st.button("📥 Export DOCX"):
        if selected_date:
            try:
                content = api_export_docx(selected_date, export_lang)
                st.download_button(
                    "📄 Download Word file",
                    data=content,
                    file_name=f"UNISOLE_UPSC_Daily_Notes_{selected_date}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_{selected_date}_{export_lang}"
                )
            except Exception as e:
                st.error(f"Export failed: {e}")
        else:
            st.warning("Enter a date first.")

st.markdown("---")

# ---------- Fetch notes from API ----------
items: List[Dict[str, Any]] = []
if selected_date:
    try:
        items = api_list_notes(selected_date)
    except Exception as e:
        st.error(f"Backend API not reachable: {e}")

if not items:
    st.info("No notes for this date yet. Save some from the Ingest page.")
    st.stop()

# Filter by category (case-insensitive)
if category_filter != "All":
    def cat_match(x):
        c = (x.get("category") or "general").lower()
        return c == category_filter.lower()
    items = [it for it in items if cat_match(it)]

total = len(items)
per_page = 10
pages = (total + per_page - 1) // per_page

pg1, pg2 = st.columns([6,1])
with pg1:
    st.markdown(f"<span class='pagination'>Total notes: <b>{total}</b> | Pages: <b>{max(pages,1)}</b></span>", unsafe_allow_html=True)
with pg2:
    page_idx = st.number_input("Page", min_value=1, max_value=max(1, pages), value=1, step=1)

start = (page_idx - 1) * per_page
end = min(start + per_page, total)
page_items = items[start:end]

# ---------- Render Cards ----------
for idx, it in enumerate(page_items, start=start + 1):
    cat = (it.get("category","general") or "general").replace("_"," ").title()
    rel = int(it.get("relevance", 0))
    title = it.get("title","(No title)")
    source = it.get("source","")
    published = it.get("publishedAt","")
    url = it.get("url","")

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

    if it.get("summary_en"):
        st.markdown("**✅ Summary (English):**")
        st.write(it["summary_en"])

    prelims = clean_bullets(it.get("prelims_points", []))
    mains = clean_bullets(it.get("mains_angles", []))
    if prelims:
        st.markdown("**📌 Prelims Pointers:**")
        st.markdown("- " + "\n- ".join(prelims))
    if mains:
        st.markdown("**📝 Mains Analysis:**")
        st.markdown("- " + "\n- ".join(mains))

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

    c1, c2, _ = st.columns([1,1,6])
    if c1.button("🗑️ Delete", key=f"del_{selected_date}_{idx}"):
        try:
            api_delete_one(selected_date, title=title, url=url)
            st.success("Deleted.")
            st.rerun()
        except Exception as e:
            st.error(f"Delete failed: {e}")

    if c2.button("📋 Copy Title", key=f"copy_{selected_date}_{idx}"):
        st.code(title)

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.info("Notes served by FastAPI. Use **🔄 Refresh Notes** to fetch latest from backend.")
