import chromadb
from chromadb.config import Settings as ChromaSettings
from src.core.config import get_settings

settings = get_settings()

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
        self.collection = self.client.get_or_create_collection(name=settings.COLLECTION_NAME)

    def add_documents(self, documents: list[str], metadatas: list[dict], ids: list[str]):
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

# Singleton instance
vector_store = VectorStore()
