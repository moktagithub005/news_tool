# pages/6_My_Saved_Notes.py
# 📚 My Saved Notes — Clean UPSC Cards • Filter • Pagination • DOCX Export • Delete

import os
import json
from datetime import datetime
from typing import Dict, List, Any

import streamlit as st

from utils.config import DATA_DIR, UPSC_CATEGORIES
from utils.docx_exporter import export_notes_to_docx

st.set_page_config(page_title="My Saved Notes", page_icon="📚", layout="wide")
st.title("📚 My Saved Notes")
st.caption("Review, filter, export, or delete your saved UPSC notes.")

SAVED_NOTES_PATH = os.path.join(DATA_DIR, "saved_notes.json")
os.makedirs(DATA_DIR, exist_ok=True)

# -----------------------------
# Helpers
# -----------------------------
def load_saved() -> Dict[str, List[Dict[str, Any]]]:
    if not os.path.exists(SAVED_NOTES_PATH):
        return {}
    try:
        with open(SAVED_NOTES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_saved(data: Dict[str, List[Dict[str, Any]]]) -> None:
    with open(SAVED_NOTES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def notes_for_date(data: Dict[str, List[Dict[str, Any]]], date_str: str) -> List[Dict[str, Any]]:
    return data.get(date_str, [])

def to_notes_by_cat(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    # Convert flat list -> {category: [items]}
    cats = {c: [] for c in UPSC_CATEGORIES}
    cats["general"] = []
    for it in items:
        c = (it.get("category") or "general")
        if c not in cats:
            c = "general"
        cats[c].append(it)
    # Sort each by relevance desc
    for k in cats:
        cats[k].sort(key=lambda x: int(x.get("relevance", 0)), reverse=True)
    return cats

# -----------------------------
# Card CSS (Blue/White theme)
# -----------------------------
CARD_CSS = """
<style>
.upsc-card {
    background: #ffffff;
    border: 1px solid #e6eef8;
    border-left: 5px solid #1f6feb;
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 14px;
    box-shadow: 0 1px 3px rgba(31,111,235,0.06);
}
.upsc-card h4 { margin: 4px 0 6px 0; }
.badge {
    display:inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px;
    background:#eaf2ff; color:#1f6feb; border: 1px solid #cfe0ff; margin-right:6px;
}
.meta { color:#6b7785; font-size: 13px; margin-bottom:6px; }
.section-title { font-weight: 600; margin-top: 8px; margin-bottom: 4px; }
.sep { height: 1px; background:#eef3fb; margin: 10px 0; }
.smallmuted { color:#8a97a6; font-size: 12px; }
.pagination { color:#6b7785; font-size: 13px; }
</style>
"""
st.markdown(CARD_CSS, unsafe_allow_html=True)

# -----------------------------
# Load & basic checks
# -----------------------------
saved = load_saved()
if not saved:
    st.info("No saved notes yet. Go to **📥 Ingest News** and click **⭐ Save to Notes** on any item.")
    st.stop()

# -----------------------------
# Controls
# -----------------------------
all_dates = sorted(saved.keys(), reverse=True)
sel_date = st.selectbox("Select Date", all_dates, index=0, key="msn_date")

all_cats = ["All"] + [c for c in UPSC_CATEGORIES] + ["general"]
sel_cat = st.selectbox("Filter by Category", all_cats, index=0, key="msn_cat")

sort_by_relevance = st.checkbox("Sort by UPSC Relevance (High → Low)", value=True)
include_hindi_docx = st.checkbox("Include Hindi content in DOCX export?", value=False)

col_actions = st.columns(3)
with col_actions[0]:
    if st.button("🗑️ Delete ALL notes for this date", key="delete_day"):
        if sel_date in saved:
            del saved[sel_date]
            save_saved(saved)
            st.success(f"Deleted all notes for {sel_date}.")
            st.experimental_rerun()
with col_actions[1]:
    if st.button("🔄 Refresh list", key="refresh_list"):
        st.experimental_rerun()

st.markdown("---")

# -----------------------------
# Filter + sort + paginate
# -----------------------------
items = notes_for_date(saved, sel_date)

# Filter by category
if sel_cat != "All":
    items = [it for it in items if (it.get("category") == sel_cat)]

# Sort by relevance
if sort_by_relevance:
    items.sort(key=lambda x: int(x.get("relevance", 0)), reverse=True)

total = len(items)
if total == 0:
    st.info("No notes for this filter.")
    st.stop()

# Pagination (10 per page)
per_page = 10
pages = (total + per_page - 1) // per_page
pg_col1, pg_col2 = st.columns([6,1])
with pg_col1:
    st.markdown(f"<span class='pagination'>Total notes: <b>{total}</b> | Pages: <b>{pages}</b></span>", unsafe_allow_html=True)
with pg_col2:
    page_idx = st.number_input("Page", min_value=1, max_value=max(1, pages), value=1, step=1, key="msn_page")

start = (page_idx - 1) * per_page
end = min(start + per_page, total)
page_items = items[start:end]

# -----------------------------
# DOCX Export for current filtered list
# -----------------------------
exp_col1, exp_col2 = st.columns([2,3])
with exp_col1:
    if st.button("📥 Export Current List to DOCX", key="export_docx"):
        # Convert filtered items to notes_by_cat structure:
        notes_by_cat = to_notes_by_cat(items)
        buffer = export_notes_to_docx(notes_by_cat, date_str=sel_date, include_hindi=include_hindi_docx, pdf_name=f"Saved Notes ({sel_date})")
        st.download_button(
            label="📄 Download DOCX",
            data=buffer,
            file_name=f"UPSC_Saved_Notes_{sel_date}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="dl_saved_docx"
        )

st.markdown("---")

# -----------------------------
# Render Cards
# -----------------------------
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

    if it.get("summary_hi"):
        st.markdown("**🇮🇳 सार (Hindi):**")
        st.write(it["summary_hi"])

    if it.get("prelims_points"):
        st.markdown("**📌 Prelims Pointers:**")
        st.markdown("- " + "\n- ".join(it["prelims_points"]))

    if it.get("mains_angles"):
        st.markdown("**📝 Mains Analysis:**")
        st.markdown("- " + "\n- ".join(it["mains_angles"]))

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

    # Delete single note button
    if st.button("🗑️ Delete this note", key=f"del_{sel_date}_{idx}"):
        # Remove by matching title+url (unique enough for our use)
        current = saved.get(sel_date, [])
        new_list = [x for x in current if not (x.get("title")==it.get("title") and x.get("url")==it.get("url"))]
        saved[sel_date] = new_list
        save_saved(saved)
        st.success("Deleted.")
        st.experimental_rerun()

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.info(f"Notes file location: `{SAVED_NOTES_PATH}`")
