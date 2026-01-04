import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from dataclasses import asdict
from .docling_parser import PaperDocument

logger = logging.getLogger(__name__)

SUMMARY_EXTRACT_TEMPLATE = """\
You are an experienced Deep Learning Researcher.
Summarize the following content into a single, detailed paragraph associated with the section it belongs to.
Capture the key technical details, architectural decisions, and empirical results.
The summary should be self-contained and provide enough context for a reader to understand the core message of this chunk.

Content:
{context_str}

Summary:"""

class PaperIngestionPipeline:
    """
    Paper ingestion pipeline using LlamaIndex's IngestionPipeline.
    
    Flow: PaperDocument → LlamaIndex Documents → Transformations → ChromaDB
    """
    
    def __init__(
        self,
        embedding_model: Optional[str] = None,
        collection_name: Optional[str] = None,
        chunk_size: int = 1024,
        chunk_overlap: int = 100,
        chroma_persist_path: Optional[str] = None,
        meta_extraction: Optional[bool] = False
    ):
        from src.core.config import get_settings
        settings = get_settings()
        
        self.embedding_model = embedding_model # Factory handles defaults if None
        self.collection_name = collection_name or settings.COLLECTION_NAME
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chroma_persist_path = chroma_persist_path or settings.VECTOR_DB_PATH
        self.meta_extraction = meta_extraction
        self._pipeline = None
        self._vector_store = None
        
    def _get_vector_store(self):
        """Get or create ChromaDB vector store."""
        if self._vector_store is None:
            import chromadb
            from llama_index.vector_stores.chroma import ChromaVectorStore
            from src.db.vector_store import get_chroma_client
            from src.core.config import get_settings
            
            chroma_client = get_chroma_client(get_settings())
            chroma_collection = chroma_client.get_or_create_collection(
                name=self.collection_name
            )
            self._vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        return self._vector_store
    
    def _get_embed_model(self):
        """Get embedding model via Factory."""
        from src.core.llm_factory import LLMFactory
        return LLMFactory.get_llama_index_embedding(model_name=self.embedding_model)
    
    def _build_pipeline(self):
        """Build LlamaIndex IngestionPipeline with transformations."""
        from llama_index.core.ingestion import IngestionPipeline
        from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
        
        if self.meta_extraction:
            from llama_index.core.extractors import (
                SummaryExtractor,
                QuestionsAnsweredExtractor,
                TitleExtractor,
                KeywordExtractor,
            )
            from src.ingestion.extractors import FigureExtractor
            from src.core.llm_factory import LLMFactory
            llm = LLMFactory.get_llama_index_llm()
            transformations = [
                # Step 1: Split by Markdown structure
                MarkdownNodeParser(),
                # Step 2: Split large chunks further if needed
                SentenceSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap
                ),
                # Step 3: Extract metadata
                SummaryExtractor(
                    llm=llm, 
                    summaries=["prev", "self"],
                    prompt_template=SUMMARY_EXTRACT_TEMPLATE
                ),
                QuestionsAnsweredExtractor(llm=llm, questions=2, embedding_only=True),
                KeywordExtractor(llm=llm),
                FigureExtractor(llm=llm),
                # Step 3: Generate embeddings
                self._get_embed_model()
            ]
        else:
            transformations = [
                # Step 1: Split by Markdown structure
                MarkdownNodeParser(),
                # Step 2: Split large chunks further if needed
                SentenceSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap
                ),
                # Step 3: Generate embeddings
                self._get_embed_model()
            ]
        
        return IngestionPipeline(
            transformations=transformations,
            vector_store=self._get_vector_store(),
        )
    
    def _parsed_doc_to_documents(self, parsed_doc: PaperDocument) -> List:
        """Convert PaperDocument to LlamaIndex Documents."""
        from llama_index.core import Document
        
        documents = []
        
        # Main document with full markdown content
        if parsed_doc.markdown_content != "":
            documents.append(Document(
                text=parsed_doc.markdown_content,
                metadata={
                    "paper_id": parsed_doc.paper_id,
                    "title": parsed_doc.title,
                    "authors": parsed_doc.authors,
                    "item_type": "full_text"
                },
                id_=f"{parsed_doc.paper_id}_full"
            ))
        else:
            # Fallback if markdown is empty (shouldn't happen with new parser)
            logger.warning(f"No markdown content for {parsed_doc.paper_id}, using legacy section fallback")
            if parsed_doc.abstract:
                documents.append(Document(
                    text=parsed_doc.abstract,
                    metadata={"paper_id": parsed_doc.paper_id, "section": "abstract"},
                    id_=f"{parsed_doc.paper_id}_abstract"
                ))
            for _, section in enumerate(parsed_doc.sections):
                doc = Document(
                    text=section.content,
                    metadata={
                        "paper_id": parsed_doc.paper_id,
                        "section": section.title,
                        "id_": section.section if section.section else "",
                        "figures": {}
                    },
                    id_=f"{parsed_doc.paper_id}_section_{section.section}" if section.section else ""
                )
                doc.excluded_embed_metadata_keys = ["figures"]
                documents.append(doc)

        # Add figure captions as helper documents? 
        # Ideally figures should be embedded in markdown, but captions are useful.
        # Let's keep separate figure index if we want, but for now stick to one main doc for continuity.
        # If we add them, they should be clearly marked.
        # For this iteration, let's trust the MarkdownNodeParser to handle the text flow.
        
        logger.info(f"Created {len(documents)} source documents for {parsed_doc.paper_id}")
        return documents
    
    def ingest(self, parsed_doc: PaperDocument) -> int:
        """
        Ingest a parsed document using LlamaIndex IngestionPipeline.
        
        Args:
            parsed_doc: Parsed document from DoclingParser
            
        Returns:
            Number of nodes created
        """
        # Convert to LlamaIndex documents
        documents = self._parsed_doc_to_documents(parsed_doc)
        
        if not documents:
            logger.warning(f"No documents created for {parsed_doc.paper_id}")
            return 0
        
        # Build and run the pipeline
        pipeline = self._build_pipeline()
        
        # Run pipeline - automatically stores in vector store
        nodes = pipeline.run(documents=documents, show_progress=True, num_workers=4)
        
        logger.info(f"Ingested {len(nodes)} nodes for {parsed_doc.paper_id}")
        return len(nodes)
    


# Alias for backward compatibility
IngestionPipeline = PaperIngestionPipeline


# Convenience function for background ingestion
async def ingest_paper_async(
    paper_id: str,
    pdf_path: Path,
    update_status_callback=None
):
    """
    Async wrapper for paper ingestion.
    Used by background tasks in FastAPI.
    """
    from .docling_parser import DoclingParser
    
    try:
        if update_status_callback:
            await update_status_callback(paper_id, "parsing")
        
        # Parse PDF
        parser = DoclingParser()
        parsed_doc = parser.parse(pdf_path, paper_id)
        
        if update_status_callback:
            await update_status_callback(paper_id, "embedding")
        
        # Ingest using LlamaIndex pipeline
        pipeline = PaperIngestionPipeline()
        chunk_count = pipeline.ingest(parsed_doc)
        
        if update_status_callback:
            await update_status_callback(paper_id, "completed", chunk_count)
        
        return chunk_count
        
    except Exception as e:
        logger.error(f"Ingestion failed for {paper_id}: {e}")
        if update_status_callback:
            await update_status_callback(paper_id, "failed")
        raise
