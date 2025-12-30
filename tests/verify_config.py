import sys
import os

# Ensure src is in pythonpath
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import get_settings

def verify_config():
    print("Loading settings...")
    try:
        settings = get_settings()
        print(f"VECTOR_DB_PATH: {settings.VECTOR_DB_PATH}")
        print(f"COLLECTION_NAME: {settings.COLLECTION_NAME}")
        
        # Check if other settings are still there (sanity check)
        print(f"LLM_PROVIDER: {settings.LLM_PROVIDER}")
        
        print("\nConfig loaded successfully!")
        
    except Exception as e:
        print(f"Failed to load config: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_config()
