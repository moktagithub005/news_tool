# Use a small official Python image
FROM python:3.11-slim

# avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system packages needed for PDF/OCR and building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements from the repository root (build context must be repo root)
# (Render: set build context to the repo root and Dockerfile path to api/Dockerfile)
COPY requirements_fastapi.txt /app/requirements_fastapi.txt

# Upgrade pip and install python deps
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements_fastapi.txt

# Copy only backend sources (api folder and utils). Using relative path from build context.
COPY api /app/api
COPY utils /app/utils
COPY export.py /app/export.py || true
COPY data /app/data || true
# (If you keep other backend files at repo root, copy them as needed)
# If you want to copy everything: use `COPY . /app` — but above is cleaner.

# Ensure /app is importable
ENV PYTHONPATH=/app

EXPOSE 8000

# Start Uvicorn pointing to the api package
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
