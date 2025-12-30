import json
import logging
import os
import re
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import asyncio
from src.tools.paper_tools import PaperTool
from concurrent.futures import ThreadPoolExecutor
from src.tools.rag_tool import PaperRAGTool
from crewai import Agent, Crew, LLM, Process, Task
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from src.db.sql_db import Figures,SessionLocal
# ============================================================================
# LOGGING & MONITORING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('paper_crew.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import re
from typing import Dict
from sqlalchemy.orm import Session


def inject_figures(
    answer: str,
    paper_id: str,
    session: Session
) -> str:
    """
    Replace <figure:ID> with image + caption fetched from DB.

    Args:
        answer: LLM answer containing <figure:ID>
        paper_id: paper identifier
        session: SQLAlchemy session
        FigureModel: ORM model for figures table

    Returns:
        Updated answer with figures injected
    """
    logger.info("Injecting figures....")
    # ID can be integer or alphanumeric (e.g., 1, 2a, fig3)
    pattern = r"<figure:([a-zA-Z0-9]+)>"

    def replace_fn(match):
        fig_id = match.group(1)
        logger.info(f"Figure found : {fig_id}")

        figure = session.get(
            Figures,
            (fig_id.strip(), paper_id)   # composite PK lookup
        )

        if not figure:
            return f"\n\n*[Figure {fig_id} not found]*\n\n"

        img_md = (
            f"![Figure {fig_id}](data:image/png;base64,{figure.data})"
            if figure.data
            else "*[Image unavailable]*"
        )

        caption_md = (
            f"*Figure {fig_id}: {figure.caption}*"
            if figure.caption
            else f"*Figure {fig_id}*"
        )

        return f"\n\n{img_md}\n\n{caption_md}\n\n"

    return re.sub(pattern, replace_fn, answer)




class MetricsCollector:
    """Track execution metrics for monitoring"""
    
    def __init__(self):
        self.metrics = []
    
    def log_metric(self, metric_type: str, value: Any, metadata: Dict = None):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': metric_type,
            'value': value,
            'metadata': metadata or {}
        }
        self.metrics.append(entry)
        logger.info(f"METRIC: {metric_type} = {value}")
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        if not self.metrics:
            return {}
        
        execution_times = [m['value'] for m in self.metrics if m['type'] == 'execution_time']
        return {
            'total_executions': len(execution_times),
            'avg_time': sum(execution_times) / len(execution_times) if execution_times else 0,
            'min_time': min(execution_times) if execution_times else 0,
            'max_time': max(execution_times) if execution_times else 0
        }
    
    def save_metrics(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump({
                'metrics': self.metrics,
                'summary': self.get_summary()
            }, f, indent=2)


# ============================================================================
# OLLAMA HEALTH CHECK
# ============================================================================

class OllamaHealthCheck:
    """Monitor Ollama server health"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    def check_server(self) -> bool:
        """Check if Ollama server is running"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Ollama server not reachable: {e}")
            return False
    
    def check_model(self, model_name: str) -> bool:
        """Check if specific model is available"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                # Handle both "qwen2.5:3b" and "ollama/qwen2.5:3b" formats
                clean_name = model_name.replace('ollama/', '')
                available = clean_name in model_names
                if not available:
                    logger.warning(f"⚠️ Model '{model_name}' not found. Available: {model_names}")
                return available
            return False
        except Exception as e:
            logger.error(f"❌ Failed to check model: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [m['name'] for m in models]
            return []
        except Exception:
            return []


# ============================================================================
# CHECKPOINT & RECOVERY
# ============================================================================

class CheckpointManager:
    """Manage checkpoints for crash recovery"""
    
    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
    
    def save_checkpoint(
        self, 
        paper_id: str, 
        stage: str, 
        data: Any, 
        status: str = "success"
    ):
        """Save execution checkpoint"""
        checkpoint = {
            'paper_id': paper_id,
            'stage': stage,
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'data': data
        }
        
        filename = f"{paper_id}_{stage}_{int(time.time())}.json"
        filepath = self.checkpoint_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        logger.info(f"✓ Checkpoint saved: {filepath}")
        return filepath
    
    def load_last_checkpoint(self, paper_id: str, stage: str) -> Optional[Dict]:
        """Load most recent checkpoint for recovery"""
        pattern = f"{paper_id}_{stage}_*.json"
        checkpoints = sorted(self.checkpoint_dir.glob(pattern), reverse=True)
        
        if not checkpoints:
            return None
        
        with open(checkpoints[0], 'r') as f:
            checkpoint = json.load(f)
        
        logger.info(f"↻ Loaded checkpoint: {checkpoints[0]}")
        return checkpoint
    
    def clear_checkpoints(self, paper_id: str):
        """Clear all checkpoints for a paper"""
        pattern = f"{paper_id}_*.json"
        for cp in self.checkpoint_dir.glob(pattern):
            cp.unlink()


# ============================================================================
# MEMORY MANAGEMENT
# ============================================================================

class PaperMemoryManager:
    """Manage conversation history and context"""
    
    def __init__(self, memory_file: str = "./memory/conversations.json"):
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(exist_ok=True)
        self.conversations = self._load_memory()
    
    def _load_memory(self) -> Dict:
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Corrupted memory file, starting fresh")
                return {}
        return {}
    
    def _save_memory(self):
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.conversations, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def add_conversation(
        self, 
        paper_id: str, 
        query: str, 
        answer: str, 
        metadata: Dict = None
    ):
        """Add conversation to memory"""
        if paper_id not in self.conversations:
            self.conversations[paper_id] = []
        
        # Limit memory size (keep last 100 conversations per paper)
        if len(self.conversations[paper_id]) > 100:
            self.conversations[paper_id] = self.conversations[paper_id][-100:]
        
        self.conversations[paper_id].append({
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'answer': answer[:500],  # Truncate for memory efficiency
            'metadata': metadata or {}
        })
        
        self._save_memory()
        logger.info(f"💾 Conversation saved for paper: {paper_id}")
    
    def get_history(self, paper_id: str, last_n: int = 3) -> str:
        """Get formatted conversation history (reduced for local models)"""
        if paper_id not in self.conversations:
            return ""
        
        history = self.conversations[paper_id][-last_n:]
        formatted = []
        
        for conv in history:
            formatted.append(f"Previous Q: {conv['query'][:100]}")
            formatted.append(f"Previous A: {conv['answer'][:150]}...\n")
        
        return "\n".join(formatted)


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

class RAGCache:
    """Cache RAG retrieval results"""
    
    def __init__(self, cache_file: str = "./cache/rag_cache.json", max_size: int = 1000):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(exist_ok=True)
        self.max_size = max_size
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def _save_cache(self):
        # Limit cache size
        if len(self.cache) > self.max_size:
            # Keep most recent entries
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: x[1].get('timestamp', ''),
                reverse=True
            )
            self.cache = dict(sorted_items[:self.max_size])
        
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def get(self, paper_id: str, query: str) -> Optional[str]:
        """Get cached result"""
        key = f"{paper_id}::{query}"
        cached = self.cache.get(key)
        if cached:
            return cached.get('result')
        return None
    
    def set(self, paper_id: str, query: str, result: str):
        """Cache result"""
        key = f"{paper_id}::{query}"
        self.cache[key] = {
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        self._save_cache()


# ============================================================================
# FIGURE VALIDATOR
# ============================================================================

class FigureValidator:
    """Validate and process figure references"""
    
    def __init__(self, paper_id: str, available_figures: Optional[List[str]] = None):
        self.paper_id = paper_id
        self.available_figures = set(available_figures) if available_figures else set()
    
    def validate_figure_refs(self, text: str) -> Tuple[str, List[str]]:
        """
        Validate figure references in text
        Returns: (validated_text, list_of_warnings)
        """
        warnings = []
        pattern = r'<figure:([^>]+)>'
        
        def replace_fn(match):
            fig_id = match.group(1).strip()
            
            # Normalize figure ID
            normalized_id = fig_id.lower().replace(' ', '_')
            
            # Check if figure exists (if we have metadata)
            if self.available_figures and normalized_id not in self.available_figures:
                warnings.append(f"Figure '{fig_id}' not found in paper")
                return f"[⚠️ FIGURE NOT FOUND: {fig_id}]"
            
            return f"<figure:{normalized_id}>"  # Return normalized
        
        validated_text = re.sub(pattern, replace_fn, text)
        return validated_text, warnings
    
    def extract_figure_ids(self, text: str) -> List[str]:
        """Extract all figure IDs from text"""
        pattern = r'<figure:([^>]+)>'
        return [fig.strip() for fig in re.findall(pattern, text)]


# ============================================================================
# ROBUST RAG TOOL WRAPPER
# ============================================================================

class RobustRAGTool():
    """Wrapper around RAG tool with retry logic and caching"""
    
    def __init__(self, base_tool, cache: RAGCache, max_retries: int = 3):
        self.base_tool = base_tool
        self.cache = cache
        self.max_retries = max_retries
        self.query_history = set()  # Track queries to prevent duplicates
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    def search(self, query: str) -> str:
        """Search with caching and retry logic"""
        paper_id = self.base_tool.paper_id
        
        # Check cache first
        cached = self.cache.get(paper_id, query)
        if cached:
            logger.info(f"⚡ Cache hit for query: {query[:50]}")
            return cached
        
        # Check if query already executed
        if query in self.query_history:
            logger.warning(f"⚠️ Duplicate query detected: {query[:50]}")
            return "Already searched this query. No new information."
        
        # Call actual tool
        try:
            logger.info(f"🔍 RAG search: {query[:50]}")
            start = time.time()
            result = self.base_tool._run(query)
            duration = time.time() - start
            
            logger.info(f"✓ RAG completed in {duration:.2f}s")
            
            # Track query
            self.query_history.add(query)
            
            # Cache result
            self.cache.set(paper_id, query, result)
            return result
            
        except Exception as e:
            logger.error(f"❌ RAG tool failed: {str(e)}")
            raise
    
    def reset_history(self):
        """Reset query history for new session"""
        self.query_history.clear()


# ============================================================================
# PRODUCTION PAPER CREW - OLLAMA OPTIMIZED
# ============================================================================

class ProductionPaperCrew:
    """Production-grade paper research crew optimized for local Ollama"""
    
    def __init__(
        self,
        ollama_base_url: Optional[str] = None,
        small_model: Optional[str] = None,
        large_model: Optional[str] = None,
        checkpoint_dir: str = "./checkpoints",
        enable_recovery: bool = True,
        enable_thinking: bool = False  # Disable for speed
    ):
        from src.core.config import get_settings
        settings = get_settings()
        
        self.ollama_base_url = ollama_base_url or settings.OLLAMA_BASE_URL
        self.small_model = small_model or settings.CREW_LLM_SMALL
        self.large_model = large_model or settings.CREW_LLM_LARGE
        self.enable_thinking = enable_thinking
        self.checkpoint_mgr = CheckpointManager(checkpoint_dir)
        self.memory_mgr = PaperMemoryManager()
        self.metrics = MetricsCollector()
        self.cache = RAGCache()
        self.enable_recovery = enable_recovery
        
        # Health check
        from src.core.config import get_settings
        settings = get_settings()
        if settings.LLM_PROVIDER == "ollama":
            self.health_checker = OllamaHealthCheck(ollama_base_url)
            self._verify_ollama()
    
    def _verify_ollama(self):
        """Verify Ollama is running and models are available"""
        logger.info("🔍 Checking Ollama server...")
        
        if not self.health_checker.check_server():
            raise RuntimeError(
                f"❌ Ollama server not running at {self.ollama_base_url}\n"
                "Please start Ollama: `ollama serve`"
            )
        
        logger.info("✓ Ollama server is running")
        
        # Check models
        available = self.health_checker.get_available_models()
        logger.info(f"Available models: {available}")
        
        # Verify required models
        for model in [self.small_model, self.large_model]:
            clean_model = model.replace('ollama/', '')
            if clean_model not in available:
                logger.warning(
                    f"⚠️ Model '{model}' not found. Pulling model...\n"
                    f"Run: `ollama pull {clean_model}`"
                )
    
    def _create_llms(self) -> Tuple[LLM, LLM]:
        """Create LLM instances via Factory"""
        try:
            from src.core.llm_factory import LLMFactory
            
            # Small model
            small_llm = LLMFactory.get_crew_llm(self.small_model)
            
            # Large model
            large_llm = LLMFactory.get_crew_llm(self.large_model)
            
            logger.info(f"✓ LLMs created: {self.small_model} (retrieval), {self.large_model} (analysis)")
            return small_llm, large_llm
            
        except Exception as e:
            logger.error(f"❌ Failed to create LLMs: {e}")
            raise
            

    
#     def _create_agents(
#         self,
#         paper_id: str,
#         paper_title: str,
#         rag_tool,
#         small_llm: LLM,
#         large_llm: LLM
#     ) -> Tuple[Agent, Agent]:
#         """Create production agents (simplified for local models)"""
        
#         # Retriever - uses small fast model
#         retriever = Agent(
#             role="Evidence Retriever",
#             goal=f"Retrieve relevant evidence from '{paper_title}' systematically",
#             backstory="""You retrieve evidence step-by-step.
# Rules:
# 1. Plan your searches ONCE at the start
# 2. Execute each search ONCE
# 3. Track what you've found
# 4. NEVER repeat queries
# 6. DO NOT answer questions - only retrieve""",
#             tools=[rag_tool],
#             llm=small_llm,
#             verbose=True,
#             allow_delegation=False,
#             max_iter=8,  # Limit for local models
#             memory=False,
#             embedder={
#         "provider": "ollama",
#         "config": {"model_name": "nomic-embed-text:v1.5"}
#     },
#             respect_context_window=True,
#         )
        
#         # Analyst - uses larger model for better synthesis
#         analyst = Agent(
#             role="Research Synthesizer",
#             goal="Create clear, well-structured answers from retrieved evidence",
#             backstory="""You synthesize research like a senior scientist.
# Rules:
# 1. Use ONLY retrieved evidence
# 2. Write in clear Markdown
# 3. Cite sources (e.g., "Section 3.2 states...")
# 4. Insert <figure:ID> when evidence mentions figures
# 5. Structure with headings: ##, ###
# 6. Be technical but clear
# 7. Admit when info is missing""",
#             llm=large_llm,
#             verbose=True,
#             allow_delegation=False,
#             max_iter=3,  # Keep focused
#             memory=False,
#             embedder={
#         "provider": "ollama",
#         "config": {"model_name": "nomic-embed-text:v1.5"}},
#             respect_context_window=True
#         )
        
#         return retriever, analyst
    
#     def _create_tasks(
#         self,
#         paper_id: str,
#         paper_title: str,
#         user_query: str,
#         chat_history: str,
#         retriever: Agent,
#         analyst: Agent,
#         rag_tool
#     ) -> List[Task]:
#         """Create production tasks (streamlined for efficiency)"""
        
#         # Task 1: Retrieval with plan (concise for local models)
#         retrieve_task = Task(
#             description=f"""
# PAPER: {paper_title}
# QUESTION: {user_query}

# CONTEXT (previous conversation):
# {chat_history[:300] if chat_history else "None"}

# YOUR JOB:
# PHASE 1 - Quick Plan (4-5 searches max):
# 1. [Search query 1]
# 2. [Search query 2]
# ...

# PHASE 2 - Execute:
# - Run each search ONCE
# - Note findings briefly
# - Stop when you have relevant info

# RULES:
# - NO duplicate queries
# - NO answering (retriever only)
# - NO more than 5 searches total

# OUTPUT:
# Plan:
# 1. ...
# 2. ...

# Results:
# Search 1: [brief findings]
# Search 2: [brief findings]
# """,
#             agent=retriever,
#             expected_output="Retrieval plan and evidence",
#             tools=[rag_tool]
#         )
        
#         # Task 2: Analysis (focused output)
#         analyze_task = Task(
#             description=f"""
# QUESTION: {user_query}

# Using ONLY the retrieved evidence, answer the question.

# FORMAT:
# - Use Markdown: ##, ###, **bold**, `code`
# - Cite: "According to Section X..."
# - Figures: Insert <figure:figure_N> when mentioned
# - Structure: Intro → Main Content → Conclusion

# QUALITY:
# - Technical but clear
# - Evidence-based only
# - If info missing: "⚠️ Not found in retrieved text"

# Keep answer focused and well-structured.
# """,
#             agent=analyst,
#             context=[retrieve_task],
#             expected_output="Markdown answer with <figure:ID> tags"
#         )
        
#         return [retrieve_task, analyze_task]

    def _create_improved_flow(
        self,
        paper_id: str,
        paper_title: str,
        user_query: str,
        rag_tool,
        small_llm: LLM,
        large_llm: LLM
    ) -> Tuple[List[Agent], List[Task]]:

        # Agent 1: Query Decomposer
        planner = Agent(
            role="Research Query Planner",
            goal="Break down complex questions into searchable sub-queries",
            backstory="""You analyze questions and create a search strategy within the paper.
            Output a numbered list of specific searches needed.""",
            llm=small_llm,
            verbose=True,
            memory=False,
            tools=[PaperTool()]
            
        )

        # Agent 2: Retriever (with tool)
        retriever = Agent(
            role="Paper Searcher",
            goal="Execute searches and retrieve evidence",
            backstory="""You use paper_search tool to find specific information.
            You search multiple times as needed to gather complete evidence.""",
            tools=[rag_tool],
            llm=small_llm,
            verbose=True,
            memory=True,  # Remember what was already searched
            max_iter=15
        )

        # Agent 3: Synthesizer (ALSO has tool for follow-up)
        synthesizer = Agent(
            role="Research Synthesizer",
            goal="Write comprehensive answers with evidence",
            backstory="""You synthesize information into clear answers.
            If you find gaps while writing, you can search for additional details.
            You cite sources and use <figure:X> tags appropriately.""",
            tools=[rag_tool],  # ⭐ Give analyst the tool too!
            llm=large_llm,
            verbose=True,
            memory=True,
            max_iter=10
        )

        # Agent 4: Quality Checker
        validator = Agent(
            role="Quality Validator",
            goal="Verify answer completeness and accuracy",
            backstory="""You check if answers are complete and well-supported.
            If critical information is missing, you can trigger additional searches.""",
            tools=[rag_tool],  # ⭐ Validator can also search!
            llm=large_llm,
            verbose=True,
            memory=True,
            max_iter=5
        )

        # Tasks with proper flow
        plan_task = Task(
            description=f"""
    Question: {user_query}
    Paper: {paper_title}
    Paper ID: {paper_id}
You are a research planning agent.

Your task is to create a structured search plan based on the user’s question
specifically with respect to paper.

Steps you MUST follow:
1. First determine whether the question refers to the research paper.
2. If yes, call the `paper_outline` tool to obtain the high-level structure of the paper.
3. Use the paper outline to identify which sections are relevant to the question.
4. Break the question into 1–2 focused sub-questions, each mapped to a specific paper section.
5. Output the plan as a list of sub-questions.

Rules:
- Do NOT answer the question.
- Do NOT invent paper structure.
- All sub-questions must be grounded in the paper outline.
- Each sub-question must be specific and searchable.    """,
            agent=planner,
            expected_output="Numbered list of search queries"
        )

        retrieve_task = Task(
            description="""
    Execute the search plan from the previous task.

    For each planned query:
    1. Use paper_search tool with the exact query
    2. Record what you found
    3. Note if anything is missing

    Compile all search results into a structured format:
    ## Query 1: [query]
    **Results**: [what you found]

    ## Query 2: [query]
    **Results**: [what you found]
    ...
    """,
            agent=retriever,
            context=[plan_task],
            expected_output="Structured compilation of all search results"
        )

        synthesize_task = Task(
            description=f"""
    Question: {user_query}

    Using the retrieved evidence, write a comprehensive answer.

    IMPORTANT: If while writing you realize you need more details:
    - Use paper_search to get that specific information
    - Don't make assumptions

    Format in Markdown with:
    - Clear structure (## headings)
    - Evidence citations ("According to Section X...")
    - Always Add appropriate <figure:N> placeholders where figures will be embedded in answer if figures are mentioned in retrieved text
    - Technical accuracy

    If information is genuinely missing, state it clearly.
    """,
            agent=synthesizer,
            context=[retrieve_task],
            expected_output="Complete Markdown answer with citations and figure tags"
        )

        validate_task = Task(
            description="""
    Review the answer against the original question.

    Check:
    1. Are all parts of the question answered?
    2. Is every claim supported by retrieved evidence?
    3. Are figure references appropriate?
    4. Is anything vague or unsupported?

    If you find gaps, you can:
    - Use paper_search to verify specific claims
    - Use paper_search to fill in missing information

    STRICTLY provide response in following JSON:
    {
      "status": "complete|incomplete|needs_revision",
      "coverage_score": 0-10,
      "issues": ["list", "of", "issues"],
      "missing_info": ["what's missing"],
      "recommendation": "accept|request_more_retrieval",
      "response": final answer in markdown.

    }
    """,
            agent=validator,
            context=[synthesize_task],
            expected_output="Quality assessment JSON"
        )

        return (
            [planner, retriever, synthesizer, validator],
            [plan_task, retrieve_task, synthesize_task, validate_task]
        )
    def execute(
        self,
        paper_id: str,
        paper_title: str,
        user_query: str,
        chat_history: Optional[str] = None,
        available_figures: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute with full error handling optimized for Ollama"""
        
        start_time = time.time()
        
        try:
            # Check for recovery checkpoint
            if self.enable_recovery:
                checkpoint = self.checkpoint_mgr.load_last_checkpoint(
                    paper_id, "analysis"
                )
                if checkpoint and checkpoint.get('status') == 'success':
                    # Check if query is the same
                    if checkpoint['data'].get('query') == user_query:
                        logger.info("↻ Using cached result from checkpoint!")
                        return checkpoint['data']
            
            # Get conversation history (limited for context window)
            history = chat_history or self.memory_mgr.get_history(paper_id, last_n=2)
            # Create LLMs
            small_llm, large_llm = self._create_llms()
            base_rag_tool = PaperRAGTool(paper_id)
            # Wrap RAG tool with robustness
            
            agents, tasks = self._create_improved_flow(paper_id, paper_title, user_query, base_rag_tool, small_llm, large_llm)
            # Create crew (simplified for local)
            crew = Crew(
                agents=agents,
                tasks=tasks,
                process=Process.sequential,
                verbose=True,
                memory=False,
                embedder={
        "provider": "ollama",
        "config": {
            "model_name": "nomic-embed-text:v1.5",  # or "nomic-embed-text"
             # Default Ollama URL
        }
    },
                cache=True,
                planning=False,  # Disable manager mode for speed
                max_rpm=None,  # No rate limit for local
                full_output=True
            )
            
            # Execute
            logger.info(f"🚀 Starting crew execution for: {user_query[:100]}")
            result = crew.kickoff()
            out = tasks[2].output.raw
            # Extract answer from result
            # if hasattr(result, 'raw'):
            #     result = json.loads(result.raw)
            #     answer = str(result["response"])
            # else:
            #     answer = str(result)
            answer = str(out)
            
            # # Validate figures
            # fig_validator = FigureValidator(paper_id, available_figures)
            # validated_answer, warnings = fig_validator.validate_figure_refs(answer)
            answer = inject_figures(
                answer,
                paper_id,
                SessionLocal()
            )
            return answer
            if warnings:
                for warning in warnings:
                    logger.warning(f"⚠️ {warning}")
            
            # Build response
            execution_time = time.time() - start_time
            response = {
                'status': 'success',
                'paper_id': paper_id,
                'query': user_query,
                'answer': validated_answer,
                'figures': fig_validator.extract_figure_ids(validated_answer),
                'warnings': warnings,
                'execution_time': execution_time,
                'model_info': {
                    'retriever': self.small_model,
                    'analyst': self.large_model
                },
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✓ Execution completed in {execution_time:.2f}s")
            
            # Save checkpoint
            self.checkpoint_mgr.save_checkpoint(
                paper_id, "analysis", response, "success"
            )
            
            # Save to memory (truncated)
            self.memory_mgr.add_conversation(
                paper_id, user_query, validated_answer[:500],
                {'figures': response['figures'], 'execution_time': execution_time}
            )
            
            # Log metrics
            self.metrics.log_metric(
                'execution_time', 
                execution_time,
                {
                    'paper_id': paper_id, 
                    'query_length': len(user_query),
                    'answer_length': len(validated_answer)
                }
            )
            
            return validated_answer
            
        except Exception as e:
            logger.error(f"❌ Crew execution failed: {str(e)}", exc_info=True)
            
            # Save failure checkpoint
            error_data = {
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__,
                'paper_id': paper_id,
                'query': user_query,
                'timestamp': datetime.now().isoformat()
            }
            
            self.checkpoint_mgr.save_checkpoint(
                paper_id, "analysis", error_data, "failed"
            )
            
            # Attempt recovery
            if self.enable_recovery:
                recovery_result = self._attempt_recovery(
                    paper_id, paper_title, user_query, base_rag_tool, 
                    available_figures, e
                )
                if recovery_result:
                    return recovery_result
            
            return error_data
    
    def _attempt_recovery(
        self,
        paper_id: str,
        paper_title: str,
        user_query: str,
        base_rag_tool,
        available_figures: Optional[List[str]],
        error: Exception
    ) -> Optional[Dict]:
        """Attempt recovery strategies"""
        logger.info("🔄 Attempting recovery...")
        
        try:
            # Strategy 1: Clear memory and retry with fresh context
            logger.info("Recovery: Clearing short-term memory")
            time.sleep(2)  # Give Ollama time to recover
            
            # Retry with fresh state
            result = self.execute(
                paper_id, paper_title, user_query, base_rag_tool,
                chat_history="",  # Fresh start
                available_figures=available_figures
            )
            
            if result.get('status') == 'success':
                logger.info("✓ Recovery successful!")
                result['recovered'] = True
                result['recovery_strategy'] = 'memory_clear'
                return result
                
        except Exception as e:
            logger.error(f"Recovery failed: {str(e)}")
        
        return None


# ============================================================================
# MAIN INTERFACE
# ============================================================================

def run_paper_crew(
    paper_id: str,
    paper_title: str,
    user_query: str,
    ollama_base_url: str = "http://localhost:11434",
    small_model: str = "qwen2.5:3b",
    large_model: str = "qwen2.5:7b",
    chat_history: Optional[str] = None,
    available_figures: Optional[List[str]] = None,
    enable_recovery: bool = False,
    enable_thinking: bool = False
) -> Dict[str, Any]:
    """
    Main entry point for production paper crew (Ollama optimized)
    
    Args:
        paper_id: Unique paper identifier
        paper_title: Title of the paper
        user_query: User's question
        rag_tool: Your PaperRAGTool instance
        ollama_base_url: Ollama server URL
        small_model: Fast model for retrieval (e.g., "qwen2.5:3b")
        large_model: Better model for analysis (e.g., "qwen2.5:7b" or "qwen2.5:14b")
        chat_history: Previous conversation context
        available_figures: List of figure IDs in the paper (for validation)
        enable_recovery: Enable automatic recovery on failure
        enable_thinking: Enable extended thinking (slower but better)
    
    Returns:
        {
            'status': 'success' | 'failed',
            'answer': str (Markdown formatted),
            'figures': List[str] (figure IDs to embed),
            'warnings': List[str],
            'execution_time': float,
            'model_info': dict,
            'timestamp': str
        }
    """
    
    crew = ProductionPaperCrew(
        ollama_base_url=ollama_base_url,
        small_model=small_model,
        large_model=large_model,
        enable_recovery=enable_recovery,
        enable_thinking=enable_thinking
    )
    
    result = crew.execute(
        paper_id=paper_id,
        paper_title=paper_title,
        user_query=user_query,
       chat_history=chat_history,
        available_figures=available_figures
    )
    
    return result


# ============================================================================
# POST-PROCESSING: Inject Base64 Figures
# ============================================================================

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

# if __name__ == "__main__":
#     # Example usage
    
#     # Initialize RAG tool
#     
    
#     # Run production crew
#     result = run_paper_crew(
#         paper_id="paper_123",
#         paper_title="Attention Is All You Need",
#         user_query="How does the multi-head attention mechanism work?",
#         
#     )
    
#     # Check result
#     if result['status'] == 'success':
#         print("✓ Success!")
#         print(f"Answer:\n{result['answer']}")
#         print(f"Figures to embed: {result['figures']}")
        
#         # Post-process: Inject figures (if you have them)
#         figure_map = {
#             'figure_1': 'iVBORw0KGgoAAAANS...',  # Your base64 data
#             'figure_2': 'iVBORw0KGgoAAAANS...',
#         }
#         final_answer = inject_figures(result['answer'], figure_map)
#         print(f"\nFinal answer with figures:\n{final_answer}")
#     else:
#         print(f"❌ Failed: {result.get('error')}")

# def run_paper_crew(
#     paper_id: str,
#     paper_title: str,
#     user_query: str,
#     ollama_model: str = "ollama/qwen2.5vl:7b",
#     ollama_base_url: str = "http://localhost:11434",
#     chat_history: Optional[str] = None
# ) -> str:
#     crew = create_paper_crew(
#         paper_id=paper_id,
#         paper_title=paper_title,
#         user_query=user_query,
#         ollama_model=ollama_model,
#         ollama_base_url=ollama_base_url,
#         chat_history=chat_history
#     )

#     result = crew.kickoff()
#     return str(result)
