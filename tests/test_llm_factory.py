"""Smoke tests for the LLM provider factory.

These avoid constructing real provider clients (which pull heavy optional
dependencies); they only exercise the config-validation paths.
"""

import pytest

from src.core.config import reload_settings
from src.core.llm_factory import LLMFactory


def test_get_crew_llm_unknown_provider_raises(monkeypatch):
    """An unrecognized provider must fail loud, not return None."""
    monkeypatch.setenv("LLM_PROVIDER", "does-not-exist")
    reload_settings()
    try:
        with pytest.raises(ValueError):
            LLMFactory.get_crew_llm("some-model")
    finally:
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        reload_settings()


def test_provider_accessors(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "lmstudio")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    reload_settings()
    try:
        assert LLMFactory.get_llm_provider() == "lmstudio"
        assert LLMFactory.get_embedding_provider() == "ollama"
    finally:
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
        reload_settings()
