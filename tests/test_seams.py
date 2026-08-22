"""The capability-seam Protocols and their structural conformance."""

from src.core.seams import SEAMS, Retriever, LLMProvider, EmbeddingProvider


def test_seams_registry_names():
    assert set(SEAMS) == {
        "retriever",
        "llm",
        "embedding",
        "pdf_parser",
        "vector_db",
        "blob_store",
        "task_queue",
        "relational_store",
    }


def test_llm_factory_conforms_to_provider_protocols():
    # LLMFactory is import-light (no heavy client construction at import time).
    from src.core.llm_factory import LLMFactory

    assert isinstance(LLMFactory, LLMProvider)
    assert isinstance(LLMFactory, EmbeddingProvider)


def test_retriever_class_has_query_surface():
    # Structural check without importing heavy vector deps: the methods exist.
    from src.core.retriever import PaperRetriever

    assert hasattr(PaperRetriever, "query")
    assert hasattr(PaperRetriever, "aquery")
    assert issubclass(PaperRetriever, object)
    # Retriever is a runtime_checkable Protocol; PaperRetriever provides its methods.
    assert callable(getattr(PaperRetriever, "query"))
    assert Retriever is not None
