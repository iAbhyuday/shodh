import logging
from typing import Optional, Any
from src.core.config import get_settings

logger = logging.getLogger(__name__)

class LLMFactory:
    """
    Factory for creating LLMs and Embeddings based on configuration.
    Supports LlamaIndex and CrewAI compatible objects.
    """
    
    @staticmethod
    def get_llm_provider() -> str:
        return get_settings().LLM_PROVIDER
        
    @staticmethod
    def get_embedding_provider() -> str:
        return get_settings().EMBEDDING_PROVIDER

    @classmethod
    def get_llama_index_llm(cls, model_name: Optional[str] = None):
        """Get LlamaIndex compatible LLM"""
        provider = cls.get_llm_provider()
        settings = get_settings()
        
        try:
            if provider == "ollama":
                from llama_index.llms.ollama import Ollama
                return Ollama(
                    model=model_name or settings.OLLAMA_MODEL,
                    base_url=settings.OLLAMA_BASE_URL,
                    temperature=0.7,
                    request_timeout=300.0
                )
            elif provider == "openai":
                from llama_index.llms.openai import OpenAI
                return OpenAI(
                    model=model_name or settings.OPENAI_MODEL,
                    api_key=settings.OPENAI_API_KEY
                )
            elif provider == "azure_openai":
                from llama_index.llms.azure_openai import AzureOpenAI
                return AzureOpenAI(
                    model=model_name or settings.AZURE_DEPLOYMENT_NAME,
                    deployment_name=settings.AZURE_DEPLOYMENT_NAME,
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_version=settings.AZURE_OPENAI_API_VERSION
                )
            elif provider == "gemini":
                from llama_index.llms.gemini import Gemini
                return Gemini(
                    model=model_name or settings.GEMINI_MODEL,
                    api_key=settings.GEMINI_API_KEY
                )
            else:
                raise ValueError(f"Unknown LLM provider: {provider}")
        except ImportError as e:
            logger.error(f"Failed to import provider {provider}: {e}")
            raise

    @classmethod
    def get_llama_index_embedding(cls, model_name: Optional[str] = None):
        """Get LlamaIndex compatible Embedding model"""
        provider = cls.get_embedding_provider()
        settings = get_settings()
        
        try:
            if provider == "ollama":
                from llama_index.embeddings.ollama import OllamaEmbedding
                return OllamaEmbedding(
                    model_name=model_name or settings.EMBEDDING_MODEL,
                    base_url=settings.OLLAMA_BASE_URL,
                    query_instruction="search_query: ",
                    text_instruction="search_document: "
                )
            elif provider == "openai":
                from llama_index.embeddings.openai import OpenAIEmbedding
                return OpenAIEmbedding(
                    model=model_name or settings.OPENAI_EMBEDDING_MODEL,
                    api_key=settings.OPENAI_API_KEY
                )
            elif provider == "azure_openai":
                from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
                return AzureOpenAIEmbedding(
                    model=model_name or settings.AZURE_EMBEDDING_DEPLOYMENT,
                    deployment_name=settings.AZURE_EMBEDDING_DEPLOYMENT,
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_version=settings.AZURE_OPENAI_API_VERSION
                )
            elif provider == "gemini":
                from llama_index.embeddings.gemini import GeminiEmbedding
                return GeminiEmbedding(
                    model_name=model_name or settings.GEMINI_EMBEDDING_MODEL,
                    api_key=settings.GEMINI_API_KEY,
                )
            else:
                 # Fallback to Ollama if unknown? No, strictly follow config
                 raise ValueError(f"Unknown Embedding provider: {provider}")
        except ImportError as e:
            logger.error(f"Failed to import embedding provider {provider}: {e}")
            raise

    @classmethod
    def get_crew_llm(cls, model_name: str) -> Any:
        """Get CrewAI compatible LLM"""
        provider = cls.get_llm_provider()
        settings = get_settings()
        
        # CrewAI's LLM class wraps LiteLLM, so we just need to pass the correct string identifier and params
        
        if provider == "ollama":
            from crewai import LLM
            return LLM(
                model=f"ollama/{model_name}",
                api_base=settings.OLLAMA_BASE_URL,
                temperature=0.1,
                num_ctx=4096
            )
        elif provider == "openai":
            from crewai import LLM
            # model_name here might need adjustment if passed from config defaulting to "qwen"
            # If provider is OpenAI, we ignore the passed `model_name` if it looks like an ollama model,
            # OR we expect the user to have set CREW_LLM_SMALL/LARGE correctly in config.
            # Assuming config is correct for the provider.
            return LLM(
                model=f"openai/{model_name}",
                api_key=settings.OPENAI_API_KEY,
                temperature=0.1
            )
        elif provider == "azure_openai":
            from crewai import LLM
            return LLM(
                model=f"azure/{model_name}", # Typically acts as deployment name
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_base=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                temperature=0.1
            )
        elif provider == "gemini":
            from crewai import LLM
            # Clean model name for LiteLLM (strip 'models/' prefix if present)
            clean_model = model_name.replace('models/', '')
            return LLM(
                model=f"gemini/{clean_model}",
                api_key=settings.GEMINI_API_KEY,
                temperature=0.1
            )


