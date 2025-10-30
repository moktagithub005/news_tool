# streamlit/Dockerfile (use this exactly)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# copy lightweight frontend requirements
COPY requirements_streamlit.txt .
RUN pip install --no-cache-dir -r requirements_streamlit.txt


COPY . /app

ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false"]
