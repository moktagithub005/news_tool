# utils/embeddings.py
"""
Embedding model loader
- Uses HuggingFace sentence transformer
- Cached for reuse
"""

from langchain_community.embeddings import HuggingFaceEmbeddings
from utils.config import EMBED_MODEL_NAME
import streamlit as st

@st.cache_resource(show_spinner=False)
def get_embeddings():
    """
    Load embedding model once and reuse.
    Using MiniLM (fast + accurate) ideal for news/doc data.
    """
    return HuggingFaceEmbeddings(
        model_name=EMBED_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
