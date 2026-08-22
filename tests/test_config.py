"""Smoke tests for configuration loading and CORS origin parsing."""

from src.core.config import get_settings, reload_settings


def test_settings_defaults():
    settings = get_settings()
    assert settings.APP_NAME == "Shodh"
    assert settings.LLM_PROVIDER in {
        "ollama",
        "lmstudio",
        "openai",
        "azure_openai",
        "gemini",
    }
    assert settings.CORS_ORIGINS  # non-empty default


def test_cors_origins_parsing(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com, http://b.com ,")
    settings = reload_settings()
    try:
        origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
        assert origins == ["http://a.com", "http://b.com"]
    finally:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        reload_settings()


def test_lmstudio_settings_present():
    settings = get_settings()
    assert settings.LMSTUDIO_BASE_URL.endswith("/v1")
    assert settings.LMSTUDIO_API_KEY  # non-empty (LM Studio ignores value)
