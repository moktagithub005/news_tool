# pages/2_Upload_PDFs.py
import streamlit as st
from datetime import datetime
from utils.analyzer_wrapper import analyze_pdf_and_build_notes
from utils.docx_exporter import build_docx_from_notes

st.set_page_config(page_title="Upload PDFs - UNISOLE UPSC", layout="wide")

# Custom CSS matching your news ingestion design
st.markdown("""
<style>
    .category-badge {
        background: #e3f2fd;
        color: #1976d2;
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 14px;
        font-weight: 500;
        display: inline-block;
        margin-bottom: 8px;
    }
    .relevance-badge {
        background: #4caf50;
        color: white;
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 14px;
        font-weight: 600;
        display: inline-block;
        margin-left: 8px;
    }
    .metadata {
        color: #666;
        font-size: 13px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📄 UPSC Cards (Sorted by AI Relevance)")

# Sidebar - Settings
with st.sidebar:
    st.header("⚙️ Settings")
    enable_ocr = st.checkbox("Enable OCR", value=True, 
                             help="Enable OCR for scanned PDFs")
    deep_count = st.slider("Deep Analysis Items", 3, 10, 5,
                          help="Number of top items to analyze deeply")
    min_relevance = st.slider("Min Relevance Score", 0, 10, 4,
                             help="Filter items below this relevance score (0-10)")

# Upload
uploaded_file = st.file_uploader("Upload Newspaper PDF", type=["pdf"])

if uploaded_file:
    bytes_data = uploaded_file.read()
    file_size_mb = len(bytes_data) / (1024 * 1024)
    
    # Show file info
    st.info(f"📄 File: {uploaded_file.name} ({file_size_mb:.2f} MB)")
    
    # Warn about large files on free tier
    if file_size_mb > 5:
        st.warning("""
        ⚠️ **Large File Detected**
        
        Your PDF is quite large. On Render's free tier (512MB RAM), this might fail.
        
        **Recommendations:**
        - Disable OCR if the PDF has selectable text
        - Try uploading only a few pages
        - Consider upgrading to Render Starter plan for 2GB RAM
        """)
    
    if st.button("🔎 Analyze & Generate Cards", type="primary"):
        with st.spinner("🧠 AI Analysis in progress... This may take 1-2 minutes"):
            try:
                result = analyze_pdf_and_build_notes(
                    bytes_data,
                    mode="deep",
                    deep_k=deep_count,
                    enable_ocr=enable_ocr,
                    min_relevance=min_relevance
                )
                
                # Check if analysis was successful
                if not result.get("ok", False):
                    st.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
                    st.stop()
                
                st.session_state["analysis"] = result
                st.success("✅ Analysis Complete!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error during analysis: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

# Display Results (matching news ingestion format)
if "analysis" in st.session_state:
    result = st.session_state["analysis"]
    
    # Check structure
    if not result.get("ok", False):
        st.error(f"Analysis failed: {result.get('error', 'Unknown error')}")
        st.stop()
    
    grouped = result.get("grouped", {})
    
    # Stats
    total_items = result.get("total_items", 0)
    categories = result.get("categories", [])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Cards", total_items)
    with col2:
        st.metric("📁 Categories", len(categories))
    with col3:
        st.metric("📄 Pages", result.get("pages", 0))
    
    st.markdown("---")
    
    # Display cards by category (EXACTLY like news ingestion)
    if not grouped or total_items == 0:
        st.warning("No items found. Try lowering the minimum relevance score.")
    else:
        for category, items in sorted(grouped.items(), key=lambda x: (-len(x[1]), x[0])):
            if not items:
                continue
            
            st.markdown(f"## {category.replace('_', ' ').title()}")
            
            for idx, item in enumerate(items, 1):
                with st.container():
                    # Category and Relevance badges
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f'<span class="category-badge">{category.title()}</span>', 
                                  unsafe_allow_html=True)
                    with col2:
                        rel = item.get("relevance", 0)
                        st.markdown(f'<span class="relevance-badge">⭐ Relevance: {rel}/10</span>', 
                                  unsafe_allow_html=True)
                    
                    # Icon
                    st.markdown("📰")
                    
                    # Metadata
                    timestamp = item.get("timestamp", "")
                    source = item.get("source", "PDF Document")
                    dates = item.get("dates", [])
                    date_str = ", ".join(dates) if dates else timestamp
                    st.markdown(f'<div class="metadata">📅 {date_str} • 🔗 {source}</div>', 
                              unsafe_allow_html=True)
                    
                    # Summary (English)
                    st.markdown("### ✅ Summary (English):")
                    
                    title = item.get("title", "")
                    if title:
                        st.markdown(f"**{title}**")
                    
                    summary = item.get("summary", item.get("summary_en", ""))
                    if summary:
                        st.markdown(summary)
                    
                    # Hindi summary if available
                    summary_hi = item.get("summary_hi", "")
                    if summary_hi:
                        st.markdown("### सार (हिंदी):")
                        st.markdown(summary_hi)
                    
                    # Schemes/Acts/Policies
                    schemes = item.get("schemes_acts_policies", [])
                    if schemes:
                        st.markdown(f"**📜 Schemes/Acts/Policies:** {', '.join(schemes)}")
                    
                    # Institutions
                    institutions = item.get("institutions", [])
                    if institutions:
                        st.markdown(f"**🏛️ Institutions:** {', '.join(institutions)}")
                    
                    # Prelims Pointers
                    prelims = item.get("prelims_points", item.get("prelims", []))
                    if prelims:
                        st.markdown("### 📌 Prelims Pointers:")
                        for p in prelims[:5]:  # Show max 5
                            st.markdown(f"• {p}")
                    
                    # Key Facts
                    key_facts = item.get("key_facts", [])
                    if key_facts:
                        st.markdown("### 💡 Key Facts:")
                        for fact in key_facts[:5]:
                            st.markdown(f"• {fact}")
                    
                    # Mains Analysis
                    deep = item.get("deep", {})
                    mains = deep.get("mains_angles", item.get("mains_angles", []))
                    if mains:
                        st.markdown("### 📝 Mains Analysis:")
                        for m in mains[:3]:  # Show max 3
                            st.markdown(f"• {m}")
                    
                    # Interview Questions
                    interview = deep.get("interview_questions", item.get("interview_questions", []))
                    if interview:
                        with st.expander("💬 Interview Questions"):
                            for q in interview:
                                st.markdown(f"• {q}")
                    
                    # Action buttons
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button("⭐ Save to Notes", key=f"save_{category}_{idx}"):
                            st.success("Saved!")
                    with col2:
                        if st.button("📋 Copy Title", key=f"copy_{category}_{idx}"):
                            st.success("Title copied!")
                    
                    st.markdown("---")
    
    # Download section
    st.markdown("### 📥 Download")
    timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    col1, col2 = st.columns(2)
    with col1:
        try:
            docx_bytes = build_docx_from_notes(result, title="UNISOLE UPSC Notes")
            st.download_button(
                "⬇️ Download DOCX",
                data=docx_bytes,
                file_name=f"UPSC_Notes_{timestamp_file}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error generating DOCX: {str(e)}")
    
    with col2:
        if st.button("🗑️ Clear Analysis", use_container_width=True):
            del st.session_state["analysis"]
            st.rerun()

else:
    # Welcome message
    st.info("📤 Upload a newspaper PDF above to get started")
    st.markdown("""
    ### How it works:
    1. 📁 Upload your PDF document (English or Hindi newspapers)
    2. ⚙️ Adjust settings in the sidebar
    3. 🔎 Click "Analyze & Generate Cards"
    4. 📊 View AI-categorized UPSC notes with:
       - Clean English summaries
       - Prelims pointers (bullet points)
       - Mains analysis angles
       - Relevance scoring (0-10)
       - Proper UPSC categorization
    5. 📥 Download as DOCX for offline study
    
    ### Features:
    - ✅ Same format as news ingestion
    - 🤖 Real AI-powered analysis
    - 🇮🇳 Supports Hindi newspapers (with English summaries)
    - 📋 Category-wise organization
    - ⭐ Relevance-based filtering
    """)