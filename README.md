# UNISOLE UPSC Notes System

AI-powered news analysis and note-taking system for UPSC preparation. Automatically extracts, categorizes, and summarizes news articles and PDF documents into structured UPSC notes.

## Features

- 📰 **News Ingestion**: Fetch and analyze news from multiple sources
- 📄 **PDF Analysis**: Upload and extract UPSC-relevant content from PDFs
- 🤖 **AI Categorization**: Automatic classification into UPSC categories (Polity, Economy, International Relations, etc.)
- ⭐ **Relevance Scoring**: AI-based scoring to prioritize important topics
- 📌 **Prelims Pointers**: Extract key facts and one-liners
- 📝 **Mains Angles**: Generate analysis perspectives for mains examination
- 📥 **DOCX Export**: Download formatted notes for offline study
- 💾 **Note Management**: Save, organize, and retrieve notes by date

## Tech Stack

- **Backend**: FastAPI
- **Frontend**: Streamlit
- **PDF Processing**: PyMuPDF (fitz)
- **Text Analysis**: scikit-learn, TF-IDF
- **Document Export**: python-docx
- **Containerization**: Docker, Docker Compose

## Project Structure

```
news_tool/
├── api/
│   ├── main.py              # FastAPI application
│   ├── routes/
│   │   ├── news.py          # News ingestion endpoints
│   │   ├── pdf.py           # PDF analysis endpoints
│   │   ├── notes.py         # Notes management
│   │   ├── export.py        # DOCX export endpoints
│   │   └── rag.py           # RAG query endpoints
│   └── schemas.py           # Pydantic models
├── pages/
│   ├── 1_Daily_News.py      # News analysis page
│   ├── 2_Upload_PDFs.py     # PDF upload and analysis
│   └── 6_My_Saved_Notes.py  # Saved notes management
├── utils/
│   ├── pdf_reader.py        # PDF extraction and processing
│   ├── analyzer_wrapper.py  # Analysis logic
│   ├── docx_exporter.py     # DOCX generation
│   ├── api_client.py        # API client for Streamlit
│   └── config.py            # Configuration
├── docker-compose.yml       # Multi-container setup
├── Dockerfile.api           # API container
├── Dockerfile.streamlit     # Streamlit container
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
└── README.md
```

## Setup Instructions

### Prerequisites

- Docker & Docker Compose
- NewsAPI key (get from https://newsapi.org)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd news_tool
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` and add your API keys**
   ```env
   NEWSAPI_KEY=your_newsapi_key_here
   API_KEY=unisole-test-key
   OPENAI_API_KEY=your_openai_key_here  # Optional
   ```

4. **Build and start containers**
   ```bash
   docker compose build
   docker compose up -d
   ```

5. **Access the application**
   - Streamlit UI: http://localhost:8501
   - API Documentation: http://localhost:8000/docs

## Usage

### PDF Analysis

1. Navigate to "Upload PDFs" page
2. Upload a newspaper PDF or study material
3. Adjust settings (OCR, relevance threshold, deep analysis count)
4. Click "Analyze & Generate Cards"
5. Review categorized notes with prelims pointers and mains angles
6. Download as DOCX for offline study

### News Analysis

1. Navigate to "Daily News" page
2. Select date and categories
3. Click "Fetch & Analyze News"
4. Review generated UPSC notes
5. Save important notes for later review

### Saved Notes

1. Navigate to "My Saved Notes" page
2. Filter by date and category
3. Export notes as DOCX
4. Delete unwanted notes

## API Endpoints

### Export
- `GET /export/docx/{date}?lang=en` - Export notes as DOCX

### Notes
- `POST /notes/save` - Save a note
- `GET /notes/list/{date}` - List notes for a date
- `DELETE /notes/delete/{date}` - Delete notes for a date

### PDF
- `POST /pdf/analyze` - Analyze uploaded PDF

### News
- `POST /ingest/news` - Fetch and analyze news

Full API documentation: http://localhost:8000/docs

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `NEWSAPI_KEY` | NewsAPI.org API key | Yes | - |
| `API_KEY` | Internal API authentication | Yes | unisole-test-key |
| `OPENAI_API_KEY` | OpenAI API key (optional) | No | - |
| `API_BASE_URL` | API base URL for Streamlit | No | http://api:8000 |

### Docker Compose Services

- **api**: FastAPI backend (port 8000)
- **streamlit**: Streamlit frontend (port 8501)

## Development

### Local Development (without Docker)

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run API**
   ```bash
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Run Streamlit**
   ```bash
   streamlit run app.py
   ```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f streamlit
```

### Rebuilding After Changes

```bash
docker compose build
docker compose up -d
```

## Troubleshooting

### Import Error: fitz
```bash
pip install pymupdf
```

### API Key Error
Ensure `API_KEY` is set in `.env` and matches in both containers.

### PDF Not Processing
- Check if PyMuPDF is installed: `docker exec news_tool-api-1 python -c "import fitz; print('OK')"`
- Enable OCR if PDF is scanned (requires pytesseract)

### Export Failed
- Verify notes exist: `curl http://localhost:8000/export/debug/YYYY-MM-DD`
- Check API logs: `docker compose logs api`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Your License Here]

## Contact

[Your Contact Information]

## Acknowledgments

- NewsAPI.org for news data
- PyMuPDF for PDF processing
- FastAPI and Streamlit communities
