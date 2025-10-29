# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from fastapi.openapi.utils import get_openapi
from dotenv import load_dotenv
import os

# ✅ Load .env variables
load_dotenv()

print("DEBUG NEWS KEY =", os.getenv("NEWS_API_KEY"))


API_KEY = os.getenv("API_KEY", "unisole-test-key")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# ✅ Initialize FastAPI app
app = FastAPI(
    title="UNISOLE UPSC AI API",
    version="1.0.0",
    description="Backend API for UPSC AI News Platform",
)

# ✅ CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your domain later for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Include app routes
from api.routes import news, pdf, notes, rag, export
app.include_router(news.router)
app.include_router(pdf.router)
app.include_router(notes.router)
app.include_router(rag.router)
app.include_router(export.router)

# ✅ Health check route
@app.get("/health")
def health():
    return {"ok": True, "service": "UPSC AI API"}

# ✅ Swagger authentication (Authorize button)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="UNISOLE UPSC AI API",
        version="1.0.0",
        description="Backend API for UPSC AI SaaS Platform",
        routes=app.routes,
    )

    # Add API Key security definition
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": API_KEY_NAME,
            "description": "Enter your API key to access this API",
        }
    }

    # Apply security globally
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", [{"APIKeyAuth": []}])

    app.openapi_schema = openapi_schema
    return openapi_schema

app.openapi = custom_openapi
