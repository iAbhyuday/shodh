from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

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
    # Agentic by default. Set False for fast single-shot RAG (single-paper chat
    # only — project synthesis is always agentic).
    use_agent: bool = True

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


class GroundedIdea(BaseModel):
    """A research idea grounded in evidence retrieved from the paper."""
    hypothesis: str = Field(..., description="A specific, testable research hypothesis or direction.")
    rationale: str = Field("", description="Why this follows from the paper's findings/limitations.")
    grounded_in: List[str] = Field(default_factory=list, description="Evidence ids used, e.g. ['E2','E5'].")
    suggested_experiment: str = Field("", description="A concrete first experiment to test it.")
    difficulty: str = Field("medium", description="Rough effort: 'low' | 'medium' | 'high'.")
    novelty: str = Field("unknown", description="'unexplored' | 'incremental' | 'similar-to-existing' | 'unknown'.")
    novelty_note: str = Field("", description="Prior-art note; names/links similar work when found.")


class IdeaSet(BaseModel):
    """Structured-output target: the set of grounded ideas."""
    ideas: List[GroundedIdea] = Field(default_factory=list)


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

