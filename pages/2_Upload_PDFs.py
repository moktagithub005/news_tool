# pages/2_Upload_PDFs.py
import streamlit as st
from datetime import datetime
from utils.pdf_reader import extract_pdf_text_bytes
from utils.analyzer_wrapper import analyze_pdf_and_build_notes
from utils.docx_exporter import build_docx_from_notes

st.set_page_config(page_title="Upload PDFs - UNISOLE UPSC", layout="wide")

# Custom CSS for clean card design
st.markdown("""
<style>
    .card-container {
        background: white;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }
    .category-badge {
        background: #e3f2fd;
        color: #1976d2;
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 14px;
        font-weight: 500;
    }
    .relevance-badge {
        background: #4caf50;
        color: white;
        padding: 6px 12px;
        border-radius: 16px;
        font-size: 14px;
        font-weight: 600;
    }
    .metadata {
        color: #666;
        font-size: 13px;
        margin-bottom: 16px;
    }
    .section-title {
        font-weight: 600;
        color: #333;
        margin-top: 16px;
        margin-bottom: 8px;
        font-size: 15px;
    }
    .bullet-point {
        margin-left: 20px;
        margin-bottom: 8px;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

st.title("📄 UPSC Cards (Sorted by AI Relevance)")

# Sidebar - Simple config
with st.sidebar:
    st.header("⚙️ Settings")
    enable_ocr = st.checkbox("Enable OCR", value=False, 
                             help="Enable OCR for scanned PDFs (requires pytesseract)")
    deep_count = st.slider("Deep Analysis Items", 3, 10, 5,
                          help="Number of top items to analyze deeply")
    min_relevance = st.slider("Min Relevance", 1, 10, 4,
                             help="Minimum relevance score to display")

# Upload
uploaded_file = st.file_uploader("Upload Newspaper PDF", type=["pdf"])

if uploaded_file:
    bytes_data = uploaded_file.read()
    
    with st.spinner("📖 Reading PDF..."):
        try:
            full_text, page_texts, page_count = extract_pdf_text_bytes(bytes_data, enable_ocr=enable_ocr)
            st.success(f"✅ Extracted {page_count} pages ({len(full_text)} characters)")
        except Exception as e:
            st.error(f"❌ Error reading PDF: {str(e)}")
            st.stop()
    
    if st.button("🔎 Analyze & Generate Cards", type="primary"):
        with st.spinner("🧠 AI Analysis in progress..."):
            try:
                structured = analyze_pdf_and_build_notes(
                    full_text, 
                    deep_k=deep_count,
                    min_relevance=min_relevance
                )
                st.session_state["analysis"] = structured
                st.session_state["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.success("✅ Analysis Complete!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error during analysis: {str(e)}")

# Display Results
if "analysis" in st.session_state:
    structured = st.session_state["analysis"]
    grouped = structured.get("grouped", {})
    
    # Stats
    total_items = structured.get("total_items", 0)
    categories = structured.get("categories", [])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Cards", total_items)
    with col2:
        st.metric("📁 Categories", len(categories))
    with col3:
        st.metric("⏰ Generated", st.session_state.get("timestamp", "N/A"))
    
    st.markdown("---")
    
    # Cards display - Clean design
    for category, items in sorted(grouped.items(), key=lambda x: (-len(x[1]), x[0])):
        
        for idx, item in enumerate(sorted(items, key=lambda x: x.get("relevance", 0), reverse=True), 1):
            
            # Card container
            with st.container():
                # Header with category and relevance badges
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f'<span class="category-badge">{category.title()}</span>', unsafe_allow_html=True)
                with col2:
                    rel = item.get("relevance", 0)
                    st.markdown(f'<span class="relevance-badge">⭐ Relevance: {rel}/10</span>', unsafe_allow_html=True)
                
                # Thumbnail icon
                st.markdown("📰")
                
                # Metadata
                timestamp = item.get("timestamp", "")
                source = item.get("source", "PDF Document")
                st.markdown(f'<div class="metadata">📅 {timestamp} • 🔗 {source}</div>', unsafe_allow_html=True)
                
                # Summary section
                st.markdown("### ✅ Summary (English):")
                headline = item.get("headline", "")
                summary = item.get("summary", "")
                
                if headline:
                    st.markdown(f"**{headline}**")
                if summary and summary != headline:
                    st.markdown(summary)
                
                # Prelims Pointers
                prelims = item.get("prelims", [])
                if prelims:
                    st.markdown("### 📌 Prelims Pointers:")
                    for p in prelims[:3]:
                        st.markdown(f"• {p}")
                
                # Mains Analysis
                deep = item.get("deep", {})
                mains = deep.get("mains_angles", []) if deep else []
                if mains:
                    st.markdown("### 📝 Mains Analysis:")
                    for m in mains[:2]:
                        st.markdown(f"• {m}")
                
                st.markdown("---")
    
    # Download section
    st.markdown("### 📥 Download")
    timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    col1, col2 = st.columns(2)
    with col1:
        try:
            docx_bytes = build_docx_from_notes(structured, title="UNISOLE UPSC Notes")
            st.download_button(
                "⬇️ Download DOCX",
                data=docx_bytes,
                file_name=f"UPSC_Notes_{timestamp_file}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error generating DOCX: {str(e)}")
            st.info("💡 Install python-docx: `pip install python-docx`")
    
    with col2:
        # Clear analysis button
        if st.button("🗑️ Clear Analysis", use_container_width=True):
            del st.session_state["analysis"]
            if "timestamp" in st.session_state:
                del st.session_state["timestamp"]
            st.rerun()

else:
    # Welcome message when no analysis
    st.info("📤 Upload a newspaper PDF above to get started")
    st.markdown("""
    ### How it works:
    1. 📁 Upload your PDF document
    2. ⚙️ Adjust settings in the sidebar (optional)
    3. 🔎 Click "Analyze & Generate Cards"
    4. 📊 View clean, categorized UPSC notes
    5. 📥 Download as DOCX for offline study
    
    ### Features:
    - ✅ Clean, concise summaries (2-3 sentences max)
    - 📌 Short prelims pointers (one-liners)
    - 📝 2 focused mains angles per topic
    - ⭐ AI-based relevance scoring
    - 📂 Automatic UPSC subject categorization
    """)