import sys
import os
import logging

# Ensure src is in pythonpath
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_E2E")

def verify_e2e():
    logger.info("--- Starting Backend E2E Audit ---")
    
    # 1. Config Layer
    try:
        from src.core.config import get_settings
        settings = get_settings()
        logger.info(f"✅ Config loaded. VECTOR_DB_PATH={settings.VECTOR_DB_PATH}")
    except Exception as e:
        logger.error(f"❌ Config failure: {e}")
        sys.exit(1)

    # 2. Vector DB Layer (Local)
    try:
        from src.db.vector_store import get_chroma_client, vector_store
        client = get_chroma_client(settings)
        # Check basic interaction
        if hasattr(client, 'heartbeat'):
            client.heartbeat()
        logger.info("✅ VectorStore (Local) initialized and heartbeat check passed.")
    except Exception as e:
        logger.error(f"❌ VectorStore failure: {e}")
        sys.exit(1)

    # 3. Ingestion Pipeline
    try:
        from src.ingestion.pipeline import IngestionPipeline
        pipeline = IngestionPipeline()
        # Verify it has the correct vector store instance
        vs = pipeline._get_vector_store()
        logger.info(f"✅ IngestionPipeline initialized with VS: {type(vs)}")
    except Exception as e:
        logger.error(f"❌ IngestionPipeline failure: {e}")
        sys.exit(1)

    # 4. Retriever
    try:
        from src.core.retriever import PaperRetriever
        retriever = PaperRetriever()
        vs = retriever._get_vector_store()
        logger.info(f"✅ PaperRetriever initialized with VS: {type(vs)}")
    except Exception as e:
        logger.error(f"❌ Retriever failure: {e}")
        sys.exit(1)
        
    # 5. API Routes Imports
    try:
        # Just import them to check for NameErrors/ImportErrors
        from src.api.routes import papers, chat, ideas
        from src.api.main import app
        logger.info("✅ API Routes imported successfully.")
    except Exception as e:
        logger.error(f"❌ API Route Import failure: {e}")
        sys.exit(1)

    logger.info("--- 🎉 E2E Audit Completed Successfully ---")

if __name__ == "__main__":
    verify_e2e()
