import chromadb
from chromadb.config import Settings as ChromaSettings
from src.core.config import get_settings


def get_chroma_client(settings=None):
    """
    Get ChromaDB client based on configuration.
    Returns HttpClient if HOST is set, otherwise PersistentClient.
    """
    settings = settings or get_settings()
    if settings.VECTOR_DB_HOST:
        return chromadb.HttpClient(
            host=settings.VECTOR_DB_HOST,
            port=settings.VECTOR_DB_PORT,
            settings=ChromaSettings()
        )
    return chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)


class VectorStore:
    def __init__(self):
        settings = get_settings()
        self.client = get_chroma_client(settings)
        self.collection = self.client.get_or_create_collection(
            name=settings.COLLECTION_NAME)

    def add_documents(
            self,
            documents: list[str],
            metadatas: list[dict],
            ids: list[str]
    ):
        """
        Add documents to the vector store.
        """
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, query_text: str, n_results: int = 5):
        """
        Query the vector store.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

    def get_all(self):
        """
        Get all documents (for debugging/listing).
        """
        return self.collection.get()


_vector_store: "VectorStore | None" = None


def get_vector_store() -> "VectorStore":
    """Lazily construct and cache the process-wide VectorStore.

    Deferring construction avoids opening a Chroma client at import time (which
    made importing this module fail without a reachable store and captured
    settings before any hot-reload).
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
