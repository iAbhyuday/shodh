import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "Shodh"
    API_V1_STR: str = "/api/v1"
    DEBUG_MODE: bool = True  # Set to True in development to disable SSL verification
    
    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_JSON: bool = False   # Set to True for JSON output (production)
    LOG_FILE: str | None = None  # Optional log file path
    
    # LLM Configuration
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gpt-oss:20b"
    
    # Qdrant (Vector Database)
    VECTOR_STORE_PROVIDER: str = "qdrant"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "research_papers"
    
    # SQL Database (PostgreSQL)
    DATABASE_URL: str = "postgresql://shodh:shodh_dev@localhost:5432/shodh"
    
    # HuggingFace
    HF_TOKEN: str | None = None

    # Embeddings & Crew Models
    LLM_PROVIDER: str = "ollama"  # ollama, openai, azure_openai, gemini
    EMBEDDING_PROVIDER: str = "ollama" # ollama, openai, azure_openai, gemini
    
    # Ollama Defaults
    EMBEDDING_MODEL: str = "nomic-embed-text:v1.5"
    CREW_LLM_SMALL: str = "qwen2.5:7b"
    CREW_LLM_LARGE: str = "qwen2.5:7b"
    
    # OpenAI
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2023-05-15"
    AZURE_DEPLOYMENT_NAME: str | None = None # For LLM
    AZURE_EMBEDDING_DEPLOYMENT: str | None = None # For Embeddings
    
    # Gemini
    GEMINI_MODEL: str = "models/gemini-1.5-flash-latest"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"

    # Ingestion Configuration
    DOCLING_ENABLE_VLM: bool = False
    DOCLING_VLM_MODEL: str = "smolvlm-v1" 
    DOCLING_VLM_API_URL: str = "http://localhost:11434/v1/chat/completions"
    DOCLING_VLM_API_KEY: str | None = None
    DOCLING_VLM_PROMPT: str = "Convert this page to markdown."

    # Job Queue (Redis)
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

@lru_cache()
def get_settings():
    return Settings()

def reload_settings():
    get_settings.cache_clear()
    return get_settings()
