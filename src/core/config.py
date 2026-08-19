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
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # CORS: comma-separated list of allowed frontend origins.
    CORS_ORIGINS: str = "http://localhost:3000"

    # Authentication.
    #   single_user  -> every request maps to the built-in default tenant (no auth)
    #   jwt          -> requests must carry a Bearer JWT signed with AUTH_JWT_SECRET
    AUTH_MODE: str = "single_user"
    AUTH_JWT_SECRET: str | None = None
    AUTH_JWT_ALGORITHM: str = "HS256"
    # JWT claim that holds the user's email/identifier.
    AUTH_JWT_EMAIL_CLAIM: str = "email"
    
    # Relational DB. SQLite by default; set a Postgres URL for a shared/scaled
    # deployment, e.g. postgresql+psycopg://user:pass@host:5432/shodh
    DATABASE_URL: str = "sqlite:///./shodh.db"

    # Vector DB
    VECTOR_DB_PATH: str = "./chroma_db"
    COLLECTION_NAME: str = "research_papers"
    VECTOR_DB_HOST: str | None = None
    VECTOR_DB_PORT: int = 8000
    
    # HuggingFace
    HF_TOKEN: str | None = None

    # Embeddings & Crew Models
    LLM_PROVIDER: str = "ollama"  # ollama, lmstudio, openai, azure_openai, gemini
    EMBEDDING_PROVIDER: str = "ollama" # ollama, lmstudio, openai, azure_openai, gemini
    
    # Ollama Defaults
    EMBEDDING_MODEL: str = "nomic-embed-text:v1.5"
    CREW_LLM_SMALL: str = "qwen2.5:3b"
    CREW_LLM_LARGE: str = "qwen2.5:7b"
    
    # OpenAI
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # LM Studio (OpenAI-compatible local server). The API key is ignored by
    # LM Studio but LiteLLM/OpenAI clients require a non-empty value.
    LMSTUDIO_BASE_URL: str = "http://localhost:1234/v1"
    LMSTUDIO_API_KEY: str = "lm-studio"
    LMSTUDIO_MODEL: str = "qwen2.5-7b-instruct"
    LMSTUDIO_EMBEDDING_MODEL: str = "text-embedding-nomic-embed-text-v1.5"

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

    # CHROMA_PERSIST_PATH is removed in favor of VECTOR_DB_PATH

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
