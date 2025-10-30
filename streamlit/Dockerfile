# streamlit/Dockerfile — assumes build context = repo root
FROM python:3.11-slim

# system deps if you need heavy PDF/OCR in the container (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy requirements from their repo path (explicit)
COPY streamlit/requirements_streamlit.txt /app/requirements_streamlit.txt
RUN pip install --no-cache-dir -r /app/requirements_streamlit.txt

# copy whole repository into /app (so app.py at repo root is present)
COPY . /app

ENV PYTHONUNBUFFERED=1
ENV API_BASE_URL="https://unisole-api.onrender.com"  # default; override in Render
EXPOSE 8501

# launch streamlit from repo root (app.py is at root)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
