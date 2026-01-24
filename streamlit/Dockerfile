# streamlit/Dockerfile — assumes build context = repo root
FROM python:3.11-slim

# System dependencies for PDF/OCR processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip

# Copy and install requirements
COPY streamlit/requirements_streamlit.txt /app/requirements_streamlit.txt

# Install in stages to ensure proper dependency resolution
RUN pip install --no-cache-dir python-dotenv requests pandas streamlit && \
    pip install --no-cache-dir langchain-core langchain-community langchain && \
    pip install --no-cache-dir groq langchain-groq langchain-openai && \
    pip install --no-cache-dir -r /app/requirements_streamlit.txt

# Copy entire repository into /app
COPY . /app

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV API_BASE_URL="https://unisole-api.onrender.com"

EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD streamlit --version || exit 1

# Launch streamlit from repo root
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]