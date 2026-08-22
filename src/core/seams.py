"""Capability-seam interfaces.

Each "seam" is a swappable capability defined as a typed ``Protocol`` (the
interface), against which concrete providers are written. Depending on the
interface rather than a concrete class is what lets a deployment change one
provider — a model backend, the vector store, the task queue, blob storage —
from configuration without touching call sites.

These Protocols are structural: a class conforms simply by having the right
methods, so the existing implementations already satisfy them. The interfaces
are collected here so future providers (Postgres, Qdrant, Celery/Arq, S3, …)
have one authoritative contract to implement.

Conforming implementations today:
  - Retriever          -> src.core.retriever.PaperRetriever
  - LLMProvider        -> src.core.llm_factory.LLMFactory (classmethods)
  - EmbeddingProvider  -> src.core.llm_factory.LLMFactory (classmethods)
  - PDFParser          -> src.ingestion.docling_parser.DoclingParser
  - VectorDBClient     -> chromadb client via src.db.vector_store.get_chroma_client
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class Retriever(Protocol):
    """Retrieves relevant chunks for a query, optionally scoped to paper id(s)."""

    def query(
        self, query_text: str, paper_id: Optional[Any] = None, top_k: int = 5
    ) -> List[dict]:
        ...

    async def aquery(
        self, query_text: str, paper_id: Optional[Any] = None, top_k: int = 5
    ) -> List[dict]:
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Builds LLM clients for a configured provider (LlamaIndex + CrewAI shapes)."""

    def get_llama_index_llm(self, model_name: Optional[str] = None) -> Any:
        ...

    def get_crew_llm(self, model_name: str) -> Any:
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Builds embedding-model clients for a configured provider."""

    def get_llama_index_embedding(self, model_name: Optional[str] = None) -> Any:
        ...


@runtime_checkable
class PDFParser(Protocol):
    """Parses a PDF at ``path`` into the app's document representation."""

    def parse(self, path: Any, paper_id: str) -> Any:
        ...


@runtime_checkable
class VectorDBClient(Protocol):
    """A Chroma-like client that yields collections for storage/retrieval."""

    def get_or_create_collection(self, name: str) -> Any:
        ...


@runtime_checkable
class BlobStore(Protocol):
    """Binary object storage for PDFs, figures, and other large assets.

    A local-filesystem implementation backs single-node deployments; an S3/GCS
    implementation backs scaled ones. Consumers hold this interface, never a
    concrete backend.
    """

    def put(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        """Store ``data`` under ``key``; return a URI/locator for it."""
        ...

    def get(self, key: str) -> bytes:
        ...

    def url(self, key: str) -> str:
        """A URL a client can read the object from (may be presigned)."""
        ...

    def delete(self, key: str) -> None:
        ...


@runtime_checkable
class TaskQueue(Protocol):
    """Dispatches background work.

    The in-process implementation wraps FastAPI ``BackgroundTasks`` for
    single-node use; a Celery/Arq implementation runs durable workers for a
    scaled deployment. Consumers depend on this interface so ingestion dispatch
    does not change when the backend does.
    """

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """Schedule ``func`` to run; return an opaque job id."""
        ...


@runtime_checkable
class RelationalStore(Protocol):
    """Provides SQLAlchemy sessions over the configured relational database."""

    def session(self) -> Any:
        """Return a new database session (SQLAlchemy ``Session``)."""
        ...


# The seam names, useful for docs/config validation and tests.
SEAMS: Dict[str, type] = {
    "retriever": Retriever,
    "llm": LLMProvider,
    "embedding": EmbeddingProvider,
    "pdf_parser": PDFParser,
    "vector_db": VectorDBClient,
    "blob_store": BlobStore,
    "task_queue": TaskQueue,
    "relational_store": RelationalStore,
}
