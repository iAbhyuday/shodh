import logging
from typing import List, Optional, Any, Dict, Union
from src.core.config import get_settings

logger = logging.getLogger(__name__)

# Process-wide caches so repeated (per-request) PaperRetriever instances do not
# rebuild the Chroma client, embedding model, or index on every call. Each is
# keyed by the settings that determine the object, so a config change (e.g. via
# the /settings hot-reload) produces a fresh entry instead of reusing a stale one.
_VECTOR_STORE_CACHE: Dict[tuple, Any] = {}
_EMBED_MODEL_CACHE: Dict[tuple, Any] = {}
_INDEX_CACHE: Dict[tuple, Any] = {}


class PaperRetriever:
    """
    Paper retrieval logic using LlamaIndex.
    Decoupled from IngestionPipeline.
    """

    def __init__(
        self,
        embedding_model: Optional[str] = None,
        collection_name: Optional[str] = None,
        chroma_persist_path: Optional[str] = None,
    ):
        settings = get_settings()
        # We allow None here so that LLMFactory can pick provider-specific defaults
        self.embedding_model = embedding_model
        self.collection_name = collection_name or settings.COLLECTION_NAME
        self.chroma_persist_path = chroma_persist_path or \
            settings.VECTOR_DB_PATH

    def _vector_store_key(self) -> tuple:
        s = get_settings()
        return (self.collection_name, s.VECTOR_DB_HOST, s.VECTOR_DB_PORT, s.VECTOR_DB_PATH)

    def _embed_key(self) -> tuple:
        s = get_settings()
        return (s.EMBEDDING_PROVIDER, self.embedding_model, s.OLLAMA_BASE_URL, s.LMSTUDIO_BASE_URL)

    def _get_vector_store(self):
        """Get or create the (cached) ChromaDB vector store."""
        key = self._vector_store_key()
        vector_store = _VECTOR_STORE_CACHE.get(key)
        if vector_store is None:
            from llama_index.vector_stores.chroma import ChromaVectorStore
            from src.db.vector_store import get_chroma_client

            chroma_client = get_chroma_client(get_settings())
            chroma_collection = chroma_client.get_or_create_collection(
                name=self.collection_name
            )
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            _VECTOR_STORE_CACHE[key] = vector_store
        return vector_store

    def _get_embed_model(self):
        """Get the (cached) embedding model via the factory."""
        key = self._embed_key()
        embed_model = _EMBED_MODEL_CACHE.get(key)
        if embed_model is None:
            from src.core.llm_factory import LLMFactory
            embed_model = LLMFactory.get_llama_index_embedding(model_name=self.embedding_model)
            _EMBED_MODEL_CACHE[key] = embed_model
        return embed_model

    def _get_index(self):
        """Get the (cached) VectorStoreIndex over the live Chroma collection.

        The index is a thin view over the vector store, so caching it is safe:
        queries still read newly ingested documents from the underlying collection.
        """
        key = (self._vector_store_key(), self._embed_key())
        index = _INDEX_CACHE.get(key)
        if index is None:
            from llama_index.core import VectorStoreIndex
            index = VectorStoreIndex.from_vector_store(
                self._get_vector_store(),
                embed_model=self._get_embed_model(),
            )
            _INDEX_CACHE[key] = index
        return index

    def query(
        self,
        query_text: str,
        paper_id: Optional[Any] = None,
        top_k: int = 5
    ) -> List[dict]:
        """
        Query the vector store for relevant chunks.
        
        Args:
            query_text: Query string
            paper_id: Optional string (single paper) or list of strings (multiple papers)
            top_k: Number of results
        """
        from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

        index = self._get_index()

        filters = None
        if paper_id:
            if isinstance(paper_id, list):
                filters = MetadataFilters(filters=[
                    MetadataFilter(key="paper_id", value=paper_id, operator="in")
                ])
            else:
                filters = MetadataFilters(filters=[
                    MetadataFilter(key="paper_id", value=paper_id)
                ])

        retriever = index.as_retriever(
            similarity_top_k=top_k,
            filters=filters
        )

        nodes = retriever.retrieve(query_text)
        results = []
        for node in nodes:
            results.append({
                "content": node.text,
                "score": node.score,
                "metadata": node.metadata
            })
        return results

    async def aquery(
        self,
        query_text: str,
        paper_id: Optional[Any] = None,
        top_k: int = 5
    ) -> List[dict]:
        """
        Async query the vector store for relevant chunks.
        """
        from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

        index = self._get_index()

        filters = None
        if paper_id:
            if isinstance(paper_id, list):
                filters = MetadataFilters(filters=[
                    MetadataFilter(key="paper_id", value=paper_id, operator="in")
                ])
            else:
                filters = MetadataFilters(filters=[
                    MetadataFilter(key="paper_id", value=paper_id)
                ])
        
        retriever = index.as_retriever(
            similarity_top_k=top_k,
            filters=filters
        )
        
        nodes = await retriever.aretrieve(query_text)
        results = []
        for node in nodes:
            results.append({
                "content": node.text,
                "score": node.score,
                "metadata": node.metadata
            })
        return results

    def get_query_engine(self, paper_id: str):
        """
        Get a LlamaIndex QueryEngine for a specific paper.
        Used by the ReAct Agent Tools.
        """
        from llama_index.core import get_response_synthesizer
        from llama_index.core.retrievers import VectorIndexRetriever
        from llama_index.core.query_engine import RetrieverQueryEngine
        from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

        # 1. Get Filters
        filters = MetadataFilters(filters=[
            MetadataFilter(key="paper_id", value=paper_id)
        ])

        # 2. Reuse the cached index over the existing store.
        index = self._get_index()

        # 3. Configure Retriever (Top-5 chunks)
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=10,
            filters=filters
        )

        # 4. Configure LLM for response synthesis via Factory
        from src.core.llm_factory import LLMFactory
        # Pass None as model_name to let Factory use provider-specific default
        llm = LLMFactory.get_llama_index_llm(model_name=None)

        # 5. Configure Response Synthesizer with Ollama
        response_synthesizer = get_response_synthesizer(
            response_mode="compact",
            llm=llm
        )

        # 6. Build Query Engine
        query_engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer,
        )

        return query_engine
