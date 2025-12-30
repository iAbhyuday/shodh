from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class IdeaRequest(BaseModel):
    paper_id: str

class PaperActionRequest(BaseModel):
    paper_id: str
    title: str = ""
    summary: str = ""
    notes: str = ""  # Formatted summary (bullet points)
    authors: str = ""
    url: str = ""
    published_date: str = ""
    github_url: Optional[str] = None
    project_page: Optional[str] = None
    mindmap_json: Optional[str] = None

class ChatRequest(BaseModel):
    paper_id: Optional[str] = None
    project_id: Optional[int] = None
    message: str
    conversation_id: Optional[int] = None  # If None, creates new conversation
    history: List[Dict[str, Any]] = []  # Optional chat history (for backward compat)
    use_agent: bool = False  # If True, use Agentic RAG; else use fast Contextual RAG

class ProjectChatRequest(BaseModel):
    project_id: int
    message: str
    conversation_id: Optional[int] = None
    history: List[Dict[str, Any]] = []
    use_agent: bool = False



class ConversationCreate(BaseModel):
    paper_id: Optional[str] = None
    project_id: Optional[int] = None
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    paper_id: Optional[str] = None
    project_id: Optional[int] = None
    title: Optional[str]
    created_at: str
    message_count: int = 0


class MindMapNode(BaseModel):
    id: str
    label: str
    children: List["MindMapNode"] = []

class PaperMetrics(BaseModel):
    core_idea: str
    tags: List[str]
    approach: List[str]
    metrics: List[str]
    main_contribution: str

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    research_dimensions: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    research_dimensions: Optional[str] = None
    created_at: str
    paper_count: int = 0

class ProjectAddPaperRequest(BaseModel):
    paper_id: str
    title: Optional[str] = None
    summary: Optional[str] = None
    authors: Optional[str] = None
    url: Optional[str] = None
    published_date: Optional[str] = None

