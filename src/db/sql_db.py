from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, Table, ForeignKey, UniqueConstraint, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

from src.core.config import get_settings

# Email of the built-in single-user tenant. In single_user auth mode every
# request resolves to this user, so existing single-user behavior is preserved
# while every tenant-owned row still carries a user_id for later isolation.
DEFAULT_USER_EMAIL = "local@shodh.local"

# Relational database. Defaults to a local SQLite file; point DATABASE_URL at
# Postgres for a shared/scaled deployment. `check_same_thread` only applies to
# SQLite, so it is set conditionally.
DATABASE_URL = get_settings().DATABASE_URL
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """An account that owns papers, projects, and conversations."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPaper(Base):
    __tablename__ = "user_papers"

    id = Column(Integer, primary_key=True, index=True)
    # Owning tenant. Nullable so existing rows load; new rows always set it.
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    paper_id = Column(String, unique=True, index=True) # Arxiv ID
    title = Column(String)
    summary = Column(Text, nullable=True)  # Original abstract
    notes = Column(Text, nullable=True)  # Formatted summary (bullet points)
    authors = Column(String, nullable=True)
    published_date = Column(String, nullable=True)  # Changed to String for flexibility
    
    # Links
    url = Column(String, nullable=True)  # Paper URL (arxiv.org)
    github_url = Column(String, nullable=True)  # GitHub repository
    project_page = Column(String, nullable=True)  # Project page
    
    # Cached visualizations
    mindmap_json = Column(Text, nullable=True)  # Mindmap data as JSON string
    
    # PDF Ingestion tracking
    pdf_path = Column(String, nullable=True)  # Local path to downloaded PDF
    ingestion_status = Column(String, nullable=True)  # pending, processing, completed, failed
    chunk_count = Column(Integer, nullable=True)  # Number of chunks indexed
    ingested_at = Column(DateTime, nullable=True)  # When ingestion completed
    error_message = Column(Text, nullable=True) # Error details if failed
    
    # User interaction state
    is_favorited = Column(Boolean, default=False)
    is_saved = Column(Boolean, default=False) # Saved means 'ingested' for us
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    """Stores chat conversations linked to papers or projects."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    paper_id = Column(String, index=True, nullable=True)  # Links to UserPaper.paper_id
    project_id = Column(Integer, ForeignKey("projects.id"), index=True, nullable=True)
    title = Column(String, nullable=True)  # Auto-generated or user-defined
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", backref="conversations")


class Message(Base):
    """Stores individual messages within a conversation."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, index=True)  # Links to Conversation.id
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    citations_json = Column(Text, nullable=True)  # JSON array of citation objects
    mode = Column(String, nullable=True)  # 'agent' or 'contextual'
    created_at = Column(DateTime, default=datetime.utcnow)


class PaperStructure(Base):
    """Stores paper outline."""
    __tablename__ = "outlines"

    paper_id = Column(String, primary_key=True)
    outline = Column(String)


class Figures(Base):
    """Store figures in DB."""
    __tablename__ = "figures"
    figure_id = Column(String, primary_key=True)
    paper_id = Column(String, primary_key=True)
    section = Column(String)
    caption = Column(String)
    data = Column(String)

# --- Projects & Collections ---

project_papers = Table(
    "project_papers",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id"), primary_key=True),
    Column("paper_id", String, ForeignKey("user_papers.paper_id"), primary_key=True),
)

class Project(Base):
    """Represents a research collection or project."""
    __tablename__ = "projects"

    # Project names are unique per user (not globally) under multi-tenancy.
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_project_user_name"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    research_dimensions = Column(Text, nullable=True) # Preliminary info to guide research q&a
    created_at = Column(DateTime, default=func.now())

    # Relationship to papers via association table
    papers = relationship("UserPaper", secondary=project_papers, backref="projects")


def get_or_create_default_user(db) -> "User":
    """Return the built-in single-user tenant, creating it if needed."""
    user = db.query(User).filter(User.email == DEFAULT_USER_EMAIL).first()
    if user is None:
        user = User(email=DEFAULT_USER_EMAIL, name="Local User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_default_user_id() -> int:
    """Convenience accessor for the default tenant's id."""
    db = SessionLocal()
    try:
        return get_or_create_default_user(db).id
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Ensure the default single-user tenant exists so every row can carry a user_id.
    db = SessionLocal()
    try:
        get_or_create_default_user(db)
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
