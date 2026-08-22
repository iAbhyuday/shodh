from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.core.config import get_settings
from src.db.sql_db import init_db
from src.api.routes import papers, chat, ideas, projects, settings

logger = logging.getLogger(__name__)

# Initialize DB
init_db()

app = FastAPI()

# CORS middleware. Origins come from config (comma-separated CORS_ORIGINS);
# a wildcard cannot be combined with credentials, so pin explicit origins.
_allowed_origins = [
    origin.strip()
    for origin in get_settings().CORS_ORIGINS.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router, prefix="/api", tags=["papers"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(ideas.router, prefix="/api", tags=["ideas"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(settings.router, prefix="/api", tags=["settings"]) # Hot reload trigger

@app.get("/")
def read_root():
    return {"message": "Welcome to Shodh"}