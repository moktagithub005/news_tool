FROM python:3.11-slim

# system deps (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy requirements from parent directory
COPY ../requirements_fastapi.txt /app/requirements_fastapi.txt
RUN pip install --no-cache-dir -r /app/requirements_fastapi.txt

# copy entire project
COPY .. /app

# make sure Python will import from /app
ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]