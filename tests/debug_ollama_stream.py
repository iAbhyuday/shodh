import asyncio
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import get_settings
from src.core.llm_factory import LLMFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DEBUG_STREAM")

async def test_stream():
    settings = get_settings()
    llm = LLMFactory.get_llama_index_llm()
    
    prompt = "Count from 1 to 5."
    logger.info(f"Prompt: {prompt}")
    
    response_gen = await llm.astream_complete(prompt)
    
    full_text = ""
    logger.info("--- Start Streaming ---")
    async for chunk in response_gen:
        delta = chunk.delta
        text = chunk.text
        logger.info(f"Chunk -> Delta: {repr(delta)} | Text: {repr(text)}")
        final_delta = delta if delta else ""
        full_text += final_delta
        
    logger.info("--- End Streaming ---")
    logger.info(f"Final Reconstructed Text: {repr(full_text)}")

if __name__ == "__main__":
    asyncio.run(test_stream())
