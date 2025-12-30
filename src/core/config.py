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
    
    # Vector DB
    VECTOR_DB_PATH: str = "./chroma_db"
    COLLECTION_NAME: str = "research_papers"
    VECTOR_DB_HOST: str | None = None
    VECTOR_DB_PORT: int = 8000
    
    # HuggingFace
    HF_TOKEN: str | None = None

    # Embeddings & Crew Models
    LLM_PROVIDER: str = "ollama"  # ollama, openai, azure_openai, gemini
    EMBEDDING_PROVIDER: str = "ollama" # ollama, openai, azure_openai, gemini
    
    # Ollama Defaults
    EMBEDDING_MODEL: str = "nomic-embed-text:v1.5"
    CREW_LLM_SMALL: str = "qwen2.5:3b"
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

    # CHROMA_PERSIST_PATH is removed in favor of VECTOR_DB_PATH

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

@lru_cache()
def get_settings():
    return Settings()
