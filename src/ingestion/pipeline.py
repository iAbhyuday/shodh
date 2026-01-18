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
    Paper ingestion pipeline using LlamaIndex's transformations pipeline.
    
    Flow: PaperDocument → LlamaIndex Documents → Transformations → Qdrant
    """
    
    def __init__(
        self,
        embedding_model: Optional[str] = None,
        collection_name: Optional[str] = None,
        chunk_size: int = 1024,
        chunk_overlap: int = 100,
        meta_extraction: Optional[bool] = False
    ):
        from src.core.config import get_settings
        settings = get_settings()
        
        self.embedding_model = embedding_model  # Factory handles defaults if None
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.meta_extraction = meta_extraction
        self._pipeline = None
        self._vector_store = None
        
    def _get_embed_model(self):
        """Get embedding model via Factory."""
        from src.core.llm_factory import LLMFactory
        return LLMFactory.get_llama_index_embedding(model_name=self.embedding_model)
    
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
                    "authors": ", ".join(parsed_doc.authors) if isinstance(parsed_doc.authors, list) else str(parsed_doc.authors),
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
                        # "figures": {} # Removed to prevent ChromaDB error
                    },
                    id_=f"{parsed_doc.paper_id}_section_{section.section}" if section.section else ""
                )
                # doc.excluded_embed_metadata_keys = ["figures"]
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
        Ingest a parsed document using Qdrant.
        
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
        
        return self._ingest_to_qdrant(documents, parsed_doc.paper_id)
    
    def _ingest_to_qdrant(self, documents: List, paper_id: str) -> int:
        """Ingest documents to Qdrant with chunking."""
        from src.db.qdrant_store import QdrantVectorStore
        from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
        from llama_index.core.ingestion import run_transformations
        from src.core.llm_factory import LLMFactory

        store = QdrantVectorStore()
        
        # 1. Define Transformations (Chunking)
        transformations = [
            MarkdownNodeParser(),
            SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
        ]
        
        # Add metadata extractors if enabled
        if self.meta_extraction:
            from llama_index.core.extractors import (
                SummaryExtractor,
                QuestionsAnsweredExtractor,
                KeywordExtractor,
            )
            from src.ingestion.extractors import FigureExtractor
            
            llm = LLMFactory.get_llama_index_llm()
            transformations.extend([
                SummaryExtractor(
                    llm=llm, 
                    summaries=["prev", "self"],
                    prompt_template=SUMMARY_EXTRACT_TEMPLATE
                ),
                QuestionsAnsweredExtractor(llm=llm, questions=2, embedding_only=True),
                KeywordExtractor(llm=llm),
                FigureExtractor(llm=llm)
            ])
            
        # 2. Run Transformations
        logger.info(f"Running transformations/chunking for {paper_id}...")
        nodes = run_transformations(
            documents,
            transformations,
            show_progress=True
        )
        
        logger.info(f"Created {len(nodes)} chunks from {len(documents)} docs")

        # 3. Convert Nodes to Qdrant Docs
        qdrant_docs = []
        for node in nodes:
            qdrant_docs.append({
                'text': node.text,
                'metadata': {
                    'paper_id': paper_id,
                    **node.metadata
                }
            })
        
        # 4. Index in Qdrant
        count = store.add_documents(qdrant_docs, paper_id)
        logger.info(f"Ingested {count} documents to Qdrant for {paper_id}")
        return count


# Alias for backward compatibility
IngestionPipeline = PaperIngestionPipeline

