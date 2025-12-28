from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# SQLite database
DATABASE_URL = "sqlite:///./shodh.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserPaper(Base):
    __tablename__ = "user_papers"

    id = Column(Integer, primary_key=True, index=True)
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
    
    # User interaction state
    is_favorited = Column(Boolean, default=False)
    is_saved = Column(Boolean, default=False) # Saved means 'ingested' for us
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    """Stores chat conversations linked to papers."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(String, index=True)  # Links to UserPaper.paper_id
    title = Column(String, nullable=True)  # Auto-generated or user-defined
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
