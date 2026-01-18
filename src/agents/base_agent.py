"""
Base agent class providing common functionality for all agents.

This module reduces code duplication across agent implementations
by centralizing LLM initialization and prompt loading.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents providing common initialization patterns.
    
    Subclasses should:
    1. Set `prompt_file` class attribute to the prompt filename
    2. Implement their specific processing methods
    """
    
    # Subclasses should override this
    prompt_file: str = ""
    
    def __init__(self):
        """Initialize the agent with LLM and prompt template."""
        self.llm = self._get_llm()
        self.prompt_template = self._load_prompt()
    
    def _get_llm(self):
        """Get LlamaIndex LLM from the factory."""
        try:
            from src.core.llm_factory import LLMFactory
            return LLMFactory.get_llama_index_llm()
        except Exception as e:
            logger.warning(f"Failed to initialize LLM for {self.__class__.__name__}: {e}")
            return None
    
    def _load_prompt(self) -> str:
        """Load prompt template from external file."""
        if not self.prompt_file:
            logger.warning(f"{self.__class__.__name__} has no prompt_file defined")
            return ""
        
        prompt_path = Path(__file__).parent / "prompts" / self.prompt_file
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_path}")
            return ""
        except Exception as e:
            logger.error(f"Error loading prompt from {prompt_path}: {e}")
            return ""
    
    @property
    def is_configured(self) -> bool:
        """Check if the agent is properly configured with an LLM."""
        return self.llm is not None
