# utils/vector_store.py
"""
Compatibility-safe vector store helpers for Chroma (LangChain).
Place this file as utils/vector_store.py in your project.

Functions:
- documents_from_articles(articles) -> List[Document]
- get_vectorstore(documents, collection_name='default', persist_directory=..., embeddings_provider='openai')
- load_vectorstore(collection_name='default', persist_directory=...)
- add_documents(vectorstore, documents) -> int
- delete_collection(collection_name, persist_directory=...)
- list_collections(persist_directory=...)
"""

import os
from typing import List, Optional, Any, Dict

# ---------------------------
# Compat import: Document
# ---------------------------
import importlib

Document = None
# Try multiple candidate module paths via importlib to avoid static-analysis unresolved-import errors
for _mod in ("langchain.schema", "langchain_core.schema", "langchain_core.documents"):
    try:
        mod = importlib.import_module(_mod)
        Document = getattr(mod, "Document")
        break
    except Exception:
        Document = None

if Document is None:
    raise ImportError(
        "Could not import Document from langchain.schema or langchain_core.schema.\n"
        "Please install a compatible langchain/langchain-core version or adjust imports."
    )

# ---------------------------
# Try to import Chroma (langchain-community or langchain-chroma)
# ---------------------------
CHROMA_CLASS = None
# Try multiple candidate module paths via importlib to avoid static-analysis unresolved-import errors
for _mod in (
    "langchain_community.vectorstores",
    "langchain.vectorstores",
    "langchain_community.vectorstores.chroma",
    "langchain.chroma",
):
    try:
        mod = importlib.import_module(_mod)
        CHROMA_CLASS = getattr(mod, "Chroma")
        break
    except Exception:
        CHROMA_CLASS = None

# ---------------------------
# Try to import OpenAIEmbeddings (or fallback)
# ---------------------------
EMBEDDINGS_CLASS = None
# Use importlib to avoid static-analysis unresolved-import errors
for _mod in (
    "langchain.embeddings",
    "langchain.embeddings.openai",
    "langchain_core.embeddings",
    "langchain_core.embeddings.openai",
):
    try:
        mod = importlib.import_module(_mod)
        EMBEDDINGS_CLASS = getattr(mod, "OpenAIEmbeddings")
        break
    except Exception:
        EMBEDDINGS_CLASS = None

# ---------------------------
# Optional fallback: sentence-transformers
# ---------------------------
SENTENCE_TRANSFORMER = None
if EMBEDDINGS_CLASS is None:
    try:
        # Use importlib to avoid static-analysis unresolved-import errors when sentence-transformers is not installed
        mod = importlib.import_module("sentence_transformers")
        SENTENCE_TRANSFORMER = getattr(mod, "SentenceTransformer", None)
    except Exception:
        SENTENCE_TRANSFORMER = None


# ---------------------------
# Config defaults
# ---------------------------
DEFAULT_PERSIST_DIR = os.getenv("VECTOR_DIR", "data/vector_store")
os.makedirs(DEFAULT_PERSIST_DIR, exist_ok=True)


# ---------------------------
# Helpers
# ---------------------------
def documents_from_articles(articles: List[Dict]) -> List[Any]:
    """
    Convert list-of-article-dicts to LangChain Document objects.
    Each article dict should have keys like 'title','content','description','publishedAt','source','url','category'
    """
    docs: List[Document] = []
    for art in articles:
        content_parts = []
        if art.get("title"):
            content_parts.append(f"Title: {art.get('title')}")
        if art.get("description"):
            content_parts.append(f"Description: {art.get('description')}")
        if art.get("content"):
            content_parts.append(f"Content: {art.get('content')}")
        if art.get("publishedAt"):
            content_parts.append(f"Published: {art.get('publishedAt')}")
        if art.get("source"):
            # source might be dict or str
            source = art.get("source")
            if isinstance(source, dict):
                source_name = source.get("name") or source.get("id") or ""
            else:
                source_name = str(source)
            content_parts.append(f"Source: {source_name}")
        meta = {
            "title": art.get("title"),
            "source": art.get("source"),
            "url": art.get("url"),
            "publishedAt": art.get("publishedAt"),
            "category": art.get("category"),
        }
        page_content = "\n\n".join([p for p in content_parts if p])
        docs.append(Document(page_content=page_content, metadata=meta))
    return docs


def _build_embeddings(provider: str = "openai", **kwargs) -> Any:
    """
    Build embeddings object. provider can be 'openai' or 'sentence-transformers'.
    """
    provider = (provider or os.getenv("EMBEDDINGS_PROVIDER", "openai")).lower()

    if provider == "openai":
        if EMBEDDINGS_CLASS is None:
            raise ImportError(
                "OpenAIEmbeddings class not available. Install a compatible langchain package "
                "or set EMBEDDINGS_PROVIDER=sentence-transformers and install sentence-transformers."
            )
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_APIKEY")
        # OpenAIEmbeddings in langchain accepts different arg names on versions; try common ones
        try:
            return EMBEDDINGS_CLASS(openai_api_key=api_key)
        except TypeError:
            return EMBEDDINGS_CLASS(openai_api_key=api_key)  # attempt fallback (may raise)

    if provider == "sentence-transformers" or provider == "sbert":
        if SENTENCE_TRANSFORMER is None:
            raise ImportError("sentence-transformers not installed. pip install sentence-transformers")
        # build a simple wrapper that matches langchain embeddings minimal interface
        model_name = os.getenv("SBERT_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        model = SENTENCE_TRANSFORMER(model_name)

        class _SbertWrapper:
            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                return [list(x) for x in model.encode(texts, show_progress_bar=False)]

            def embed_query(self, text: str) -> List[float]:
                return list(model.encode([text])[0])

        return _SbertWrapper()

    raise RuntimeError(f"Unknown embeddings provider: {provider}")


def get_vectorstore(
    documents: Optional[List[Document]] = None,
    collection_name: str = "default",
    persist_directory: Optional[str] = None,
    embeddings_provider: str = "openai",
    force_recreate: bool = False,
    **chroma_kwargs,
) -> Any:
    """
    Create or load a Chroma vector store.

    - documents: list of LangChain Document objects (optional: if provided, they will be added)
    - collection_name: name of Chroma collection
    - persist_directory: folder to persist DB (default from VECTOR_DIR env)
    - embeddings_provider: 'openai' (default) or 'sentence-transformers'
    - force_recreate: if True, remove existing directory to recreate the store.
    - chroma_kwargs: extra kwargs passed to Chroma.from_documents or Chroma constructor.

    Returns: vectorstore object (LangChain/Chroma wrapper)
    """
    persist_directory = persist_directory or DEFAULT_PERSIST_DIR
    os.makedirs(persist_directory, exist_ok=True)

    # ensure Chroma is available
    if CHROMA_CLASS is None:
        raise ImportError(
            "Chroma vectorstore class not found. Install `langchain-community` or a compatible `langchain` Chroma integration.\n"
            "Try: pip install langchain-community chromadb"
        )

    emb = _build_embeddings(provider=embeddings_provider)

    # If force_recreate, remove persist dir for this collection
    collection_path = os.path.join(persist_directory, collection_name)
    if force_recreate and os.path.exists(collection_path):
        # only remove the collection files (be cautious)
        try:
            import shutil
            shutil.rmtree(collection_path)
        except Exception:
            pass

    # If documents provided, use from_documents helper
    if documents:
        try:
            # Prefer from_documents if available
            if hasattr(CHROMA_CLASS, "from_documents"):
                vs = CHROMA_CLASS.from_documents(
                    documents, 
                    embedding=emb, 
                    persist_directory=persist_directory, 
                    collection_name=collection_name, 
                    **chroma_kwargs
                )
            else:
                # older wrappers sometimes require different arg order
                vs = CHROMA_CLASS(
                    persist_directory=persist_directory, 
                    collection_name=collection_name, 
                    embedding_function=emb, 
                    **chroma_kwargs
                )
                vs.add_documents(documents)
        except Exception as e:
            # helpful error
            raise RuntimeError(f"Failed to create Chroma vectorstore: {e}")
        return vs

    # If no documents, try to load existing store
    try:
        if hasattr(CHROMA_CLASS, "from_documents"):
            # load without docs by instantiating; some implementations accept persist_directory+collection_name
            vs = CHROMA_CLASS(
                persist_directory=persist_directory, 
                collection_name=collection_name, 
                embedding=emb, 
                **chroma_kwargs
            )
        else:
            vs = CHROMA_CLASS(
                persist_directory=persist_directory, 
                collection_name=collection_name, 
                embedding_function=emb, 
                **chroma_kwargs
            )
        return vs
    except Exception as e:
        raise RuntimeError(f"Could not load vectorstore for collection '{collection_name}': {e}")


def load_vectorstore(
    collection_name: str = "default", 
    persist_directory: Optional[str] = None, 
    embeddings_provider: str = "openai", 
    **kwargs
) -> Any:
    """
    Load existing vectorstore (wrapper for get_vectorstore with no docs).
    """
    return get_vectorstore(
        documents=None, 
        collection_name=collection_name, 
        persist_directory=persist_directory, 
        embeddings_provider=embeddings_provider, 
        **kwargs
    )


def add_documents(vectorstore: Any, documents: List[Document]) -> int:
    """
    Add documents to an existing vectorstore.
    
    Args:
        vectorstore: An existing Chroma vectorstore instance
        documents: List of Document objects to add
        
    Returns:
        Number of documents added
    """
    if not documents:
        return 0
    
    try:
        # Most vectorstore implementations have add_documents method
        if hasattr(vectorstore, 'add_documents'):
            vectorstore.add_documents(documents)
            return len(documents)
        else:
            raise AttributeError("Vectorstore does not have add_documents method")
    except Exception as e:
        raise RuntimeError(f"Failed to add documents to vectorstore: {e}")


def delete_collection(collection_name: str, persist_directory: Optional[str] = None) -> bool:
    """
    Delete a collection from the vector store.
    
    Args:
        collection_name: Name of the collection to delete
        persist_directory: Directory where vectorstore is persisted
        
    Returns:
        True if deleted successfully, False otherwise
    """
    persist_directory = persist_directory or DEFAULT_PERSIST_DIR
    collection_path = os.path.join(persist_directory, collection_name)
    
    try:
        if os.path.exists(collection_path):
            import shutil
            shutil.rmtree(collection_path)
            return True
        return False
    except Exception as e:
        raise RuntimeError(f"Failed to delete collection '{collection_name}': {e}")


def list_collections(persist_directory: Optional[str] = None) -> List[str]:
    """
    List all available collections in the vector store.
    
    Args:
        persist_directory: Directory where vectorstore is persisted
        
    Returns:
        List of collection names
    """
    persist_directory = persist_directory or DEFAULT_PERSIST_DIR
    
    try:
        if not os.path.exists(persist_directory):
            return []
        
        # List subdirectories (each is typically a collection)
        collections = [
            name for name in os.listdir(persist_directory)
            if os.path.isdir(os.path.join(persist_directory, name))
        ]
        return collections
    except Exception as e:
        raise RuntimeError(f"Failed to list collections: {e}")


def get_collection_stats(vectorstore: Any) -> Dict[str, Any]:
    """
    Get statistics about a collection.
    
    Args:
        vectorstore: An existing Chroma vectorstore instance
        
    Returns:
        Dictionary with collection statistics
    """
    try:
        stats = {}
        
        # Try to get document count
        if hasattr(vectorstore, '_collection'):
            collection = vectorstore._collection
            if hasattr(collection, 'count'):
                stats['document_count'] = collection.count()
        
        # Add more stats as needed
        return stats
    except Exception as e:
        return {"error": str(e)}