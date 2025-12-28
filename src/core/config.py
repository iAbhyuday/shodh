import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Shodh"
    API_V1_STR: str = "/api/v1"
    
    # LLM Configuration
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.7vl:7b"
    
    # Vector DB
    VECTOR_DB_PATH: str = "./chroma_db"
    COLLECTION_NAME: str = "research_papers"
    
    # HuggingFace
    HF_TOKEN: str | None = None

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
