# api/Dockerfile
FROM python:3.11-slim

# Install system packages needed for PDF/text/ocr
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      poppler-utils \
      tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only the requirements file from the api folder (your file is in api/)
COPY api/requirements_fastapi.txt /app/requirements_fastapi.txt

# Install Python deps (no-cache)
RUN pip install --no-cache-dir -r /app/requirements_fastapi.txt

# Copy the whole repo into the container
COPY . /app

# Ensure package imports work (so `api.main` can be imported)
ENV PYTHONPATH=/app

EXPOSE 8000

# Use Uvicorn to run FastAPI
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
