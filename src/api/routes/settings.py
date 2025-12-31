from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from src.core.config import get_settings, reload_settings
from dotenv import set_key, load_dotenv

router = APIRouter()

class SettingsUpdate(BaseModel):
    # LLM
    LLM_PROVIDER: str
    OLLAMA_MODEL: str | None = None
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str | None = None
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str | None = None
    
    # Embeddings
    EMBEDDING_PROVIDER: str
    
    
    # Parsing / Ingestion
    DOCLING_ENABLE_VLM: bool
    DOCLING_VLM_MODEL: str | None = None
    DOCLING_VLM_API_URL: str | None = None
    DOCLING_VLM_API_KEY: str | None = None
    DOCLING_VLM_PROMPT: str | None = None

@router.get("/settings")
def get_current_settings():
    """Get current configuration active in memory."""
    settings = get_settings()
    # Be careful not to expose full keys in production, 
    # but for local app it's often fine or we mask them.
    # Masking for safety:
    mask = lambda s: f"sk-...{s[-4:]}" if s and len(s) > 10 else ""
    
    return {
        "LLM_PROVIDER": settings.LLM_PROVIDER,
        "OLLAMA_MODEL": settings.OLLAMA_MODEL,
        "OPENAI_MODEL": settings.OPENAI_MODEL,
        "GEMINI_MODEL": settings.GEMINI_MODEL,
        "EMBEDDING_PROVIDER": settings.EMBEDDING_PROVIDER,
        
        "DOCLING_ENABLE_VLM": settings.DOCLING_ENABLE_VLM,
        "DOCLING_VLM_MODEL": settings.DOCLING_VLM_MODEL,
        "DOCLING_VLM_API_URL": settings.DOCLING_VLM_API_URL,
        "DOCLING_VLM_PROMPT": settings.DOCLING_VLM_PROMPT,
        
        # We generally don't return full keys to UI for security,
        # but UI needs to know if they are set. A simple explicit bool or masked val works.
        "OPENAI_API_KEY_MASKED": mask(settings.OPENAI_API_KEY),
        "GEMINI_API_KEY_MASKED": mask(settings.GEMINI_API_KEY),
        "DOCLING_VLM_API_KEY_MASKED": mask(settings.DOCLING_VLM_API_KEY),
    }

@router.post("/settings/update")
def update_settings(updates: SettingsUpdate):
    """
    Update settings in .env and hot-reload config.
    """
    env_path = ".env"
    
    # 1. Update .env file (Persistence)
    # We use python-dotenv's set_key to write to file
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write("")
            
    try:
        set_key(env_path, "LLM_PROVIDER", updates.LLM_PROVIDER)
        set_key(env_path, "EMBEDDING_PROVIDER", updates.EMBEDDING_PROVIDER)
        set_key(env_path, "DOCLING_ENABLE_VLM", str(updates.DOCLING_ENABLE_VLM))
        
        if updates.OLLAMA_MODEL:
            set_key(env_path, "OLLAMA_MODEL", updates.OLLAMA_MODEL)
            
        if updates.OPENAI_API_KEY:
            set_key(env_path, "OPENAI_API_KEY", updates.OPENAI_API_KEY)
        if updates.OPENAI_MODEL:
             set_key(env_path, "OPENAI_MODEL", updates.OPENAI_MODEL)
             
        if updates.GEMINI_API_KEY:
            set_key(env_path, "GEMINI_API_KEY", updates.GEMINI_API_KEY)
        if updates.GEMINI_MODEL:
            set_key(env_path, "GEMINI_MODEL", updates.GEMINI_MODEL)
            
        if updates.DOCLING_VLM_MODEL:
            set_key(env_path, "DOCLING_VLM_MODEL", updates.DOCLING_VLM_MODEL)
        
        if updates.DOCLING_VLM_API_URL:
            set_key(env_path, "DOCLING_VLM_API_URL", updates.DOCLING_VLM_API_URL)
        if updates.DOCLING_VLM_API_KEY:
            set_key(env_path, "DOCLING_VLM_API_KEY", updates.DOCLING_VLM_API_KEY)
        if updates.DOCLING_VLM_PROMPT:
            set_key(env_path, "DOCLING_VLM_PROMPT", updates.DOCLING_VLM_PROMPT)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write to .env: {e}")
        
    # 2. Update os.environ (Immediate effect before reload)
    os.environ["LLM_PROVIDER"] = updates.LLM_PROVIDER
    os.environ["EMBEDDING_PROVIDER"] = updates.EMBEDDING_PROVIDER
    os.environ["DOCLING_ENABLE_VLM"] = str(updates.DOCLING_ENABLE_VLM)
    
    if updates.OLLAMA_MODEL:
        os.environ["OLLAMA_MODEL"] = updates.OLLAMA_MODEL
    if updates.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = updates.OPENAI_API_KEY
    if updates.GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = updates.GEMINI_API_KEY
    if updates.DOCLING_VLM_MODEL:
        os.environ["DOCLING_VLM_MODEL"] = updates.DOCLING_VLM_MODEL
    
    if updates.DOCLING_VLM_API_URL:
        os.environ["DOCLING_VLM_API_URL"] = updates.DOCLING_VLM_API_URL
    if updates.DOCLING_VLM_API_KEY:
        os.environ["DOCLING_VLM_API_KEY"] = updates.DOCLING_VLM_API_KEY
    if updates.DOCLING_VLM_PROMPT:
        os.environ["DOCLING_VLM_PROMPT"] = updates.DOCLING_VLM_PROMPT

    # 3. Force Reload Config
    new_settings = reload_settings()
    
    return {"status": "success", "message": "Settings updated and hot-reloaded.", "current_llm": new_settings.LLM_PROVIDER}
