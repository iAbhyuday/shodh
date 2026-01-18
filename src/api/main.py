from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import certifi

# Fix frequency SSL errors on macOS/Python environments
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from src.core.config import get_settings
from src.core.logging import setup_logging, get_logger
from src.db.sql_db import init_db
from src.api.routes import papers, chat, ideas, projects, settings, events, figures

# Initialize logging first
_settings = get_settings()
setup_logging(
    level=_settings.LOG_LEVEL,
    json_output=_settings.LOG_JSON,
    log_file=_settings.LOG_FILE
)

logger = get_logger(__name__)

# Initialize DB
init_db()

from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(
    title="Shodh API",
    description="AI-powered research assistant API for paper discovery, analysis, and synthesis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Ensure PDF directory exists
PDF_DIR = "data/pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

# Mount PDFs
app.mount("/pdfs", StaticFiles(directory=PDF_DIR), name="pdfs")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router, prefix="/api", tags=["papers"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(ideas.router, prefix="/api", tags=["ideas"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(settings.router, prefix="/api", tags=["settings"])
app.include_router(events.router, prefix="/api", tags=["events"])  # SSE events
app.include_router(figures.router, tags=["figures"])  


@app.middleware("http")
async def log_requests(request, call_next):
    """Basic request logging middleware."""
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    return response


@app.get("/")
def read_root():
    return {"message": "Welcome to Shodh"}


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "shodh-api"}