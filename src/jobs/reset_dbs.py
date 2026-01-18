import logging
import sys
from sqlalchemy import text
from src.core.config import get_settings
from src.db.sql_db import engine, Base
from src.db.qdrant_store import get_qdrant_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_databases():
    settings = get_settings()
    
    # 1. Clear Qdrant
    try:
        logger.info(f"Connecting to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}...")
        client = get_qdrant_client(settings)
        
        # Check if collection exists
        if client.collection_exists(settings.QDRANT_COLLECTION):
            logger.warning(f"Deleting Qdrant collection: {settings.QDRANT_COLLECTION}")
            client.delete_collection(settings.QDRANT_COLLECTION)
            logger.info("Qdrant collection deleted.")
        else:
            logger.info("Qdrant collection not found (already clean).")
            
    except Exception as e:
        logger.error(f"Failed to clear Qdrant: {e}")
        return False

    # 2. Clear PostgreSQL
    try:
        logger.info(f"Connecting to PostgreSQL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else '...'}")
        
        # Drop all tables
        logger.warning("Dropping all PostgreSQL tables...")
        Base.metadata.drop_all(bind=engine)
        
        # Recreate tables
        logger.info("Recreating PostgreSQL tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("PostgreSQL reset complete.")
        
    except Exception as e:
        logger.error(f"Failed to clear PostgreSQL: {e}")
        return False
        
    return True

if __name__ == "__main__":
    confirm = input("Are you SURE you want to DELETE ALL DATA? [y/N]: ")
    if confirm.lower() != 'y':
        logger.info("Aborted.")
        sys.exit(0)
        
    if reset_databases():
        logger.info("✓ Databases cleared successfully.")
    else:
        logger.error("✗ Failed to clear databases.")
