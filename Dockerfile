# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# system deps (optional: poppler/tesseract if you add OCR to API)
# RUN apt-get update && apt-get install -y poppler-utils tesseract-ocr && rm -rf /var/lib/apt/lists/*

COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt

# copy project
COPY . .

# expose FastAPI
EXPOSE 8000

# env defaults
ENV CORS_ORIGINS="*"

# start server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]


