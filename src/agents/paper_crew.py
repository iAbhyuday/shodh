"""
CrewAI Paper Research Crew
3-Agent pipeline: Query Enricher → Retriever → Analyst
"""
from crewai import Agent, Task, Crew, Process, LLM
from typing import Optional

from src.agents.paper_rag_tool import PaperRAGTool


def create_paper_crew(
    paper_id: str,
    paper_title: str,
    user_query: str,
    ollama_model: str = "ollama/qwen2.5vl:7b",
    ollama_base_url: str = "http://localhost:11434",
    chat_history: Optional[str] = None
):
    """
    Create a CrewAI crew for paper-based Q&A.
    
    Args:
        paper_id: The paper ID for RAG retrieval
        paper_title: Title of the paper (for context)
        user_query: The user's question
        ollama_model: Ollama model name
        ollama_base_url: Ollama API base URL
        chat_history: Optional formatted chat history
    
    Returns:
        result: The final answer from the crew
        crew: The Crew object (for debugging/inspection)
    """
    # Initialize LLM (CrewAI uses 'api_base' for custom endpoints)
    llm = LLM(
        model=ollama_model,
        api_base=ollama_base_url,
    )
    
    # Create RAG Tool
    rag_tool = PaperRAGTool(paper_id=paper_id)
    
    # === Agent 1: Query Enricher ===
    query_enricher = Agent(
        role="Query Enricher",
        goal="Expand and clarify user queries for better academic paper retrieval",
        backstory="""You are an expert at understanding user intent and reformulating 
        queries for academic paper search. You expand short queries with relevant 
        synonyms, technical terms, and related concepts to improve retrieval accuracy.
        You do NOT answer questions - you only improve the query.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # === Agent 2: Retriever ===
    retriever = Agent(
        role="Paper Retriever",
        goal=f"Find relevant information from the paper '{paper_title}'",
        backstory="""You are an expert researcher who can extract specific information 
        from academic papers. You use the paper_search tool to find relevant sections, 
        data, and results. You always cite which section the information came from.""",
        tools=[rag_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # === Agent 3: Analyst ===
    analyst = Agent(
        role="Research Analyst",
        goal="Synthesize retrieved information into clear, structured answers",
        backstory="""You are a senior researcher who explains complex academic findings 
        in clear, accessible language. You create well-structured responses using 
        Markdown formatting with bullet points, bold text, and organized sections.
        You always base your answers on the retrieved context, never making up information.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # === Task 1: Enrich Query ===
    enrich_task = Task(
        description=f"""Analyze and expand this user question for academic paper search:

USER QUESTION: {user_query}

PAPER TITLE: {paper_title}

{f"CHAT HISTORY: {chat_history}" if chat_history else ""}

Your job is to:
1. Identify the core intent of the question
2. Add relevant synonyms and technical terms
3. Include related concepts that might help find relevant sections
4. Output an ENRICHED SEARCH QUERY (not an answer)

Example:
- User: "What about Table 1?"
- Enriched: "Table 1 results data performance metrics quantitative evaluation comparison"
""",
        agent=query_enricher,
        expected_output="An enriched search query with relevant keywords and terms"
    )
    
    # === Task 2: Retrieve Context ===
    retrieve_task = Task(
        description=f"""Use the paper_search tool to find relevant information.

ORIGINAL QUESTION: {user_query}
ENRICHED QUERY: Use the enriched query from the previous task to search.

Search the paper multiple times if needed to gather comprehensive context.
Report all relevant sections, data, and findings you discover.
""",
        agent=retriever,
        expected_output="Relevant excerpts and data from the paper with section citations",
        context=[enrich_task]
    )
    
    # === Task 3: Analyze and Answer ===
    analyze_task = Task(
        description=f"""Based on the retrieved context, answer the user's question.

ORIGINAL QUESTION: {user_query}

{f"CHAT HISTORY: {chat_history}" if chat_history else ""}

Guidelines:
- Use Markdown formatting (headers, bullets, bold)
- Give strucutred abd bullted answers.
- Be deep technical but comprehensive
- Cite which sections your information comes from
- If the context doesn't contain the answer, say so clearly
- Never make up information not in the context
""",
        agent=analyst,
        expected_output="A clear, well-structured Markdown answer to the user's question",
        context=[retrieve_task]
    )
    
    # === Assemble Crew ===
    crew = Crew(
        agents=[retriever, analyst],
        tasks=[retrieve_task, analyze_task],
        process=Process.sequential,
        verbose=True
    )
    
    return crew


def run_paper_crew(
    paper_id: str,
    paper_title: str,
    user_query: str,
    ollama_model: str = "ollama/qwen2.5vl:7b",
    ollama_base_url: str = "http://localhost:11434",
    chat_history: Optional[str] = None
) -> str:
    """
    Run the paper crew and return the final answer.
    
    Returns:
        The analyst's final response as a string
    """
    crew = create_paper_crew(
        paper_id=paper_id,
        paper_title=paper_title,
        user_query=user_query,
        ollama_model=ollama_model,
        ollama_base_url=ollama_base_url,
        chat_history=chat_history
    )
    
    result = crew.kickoff()
    return str(result)
