from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from src.db.sql_db import SessionLocal, PaperStructure


class PaperInput(BaseModel):
    """Input schema for PaperTool."""
    paper_id: str = Field(..., description="The paper identifier.")


class PaperTool(BaseTool):
    """Tool to fetch outline for specific paper by paper_id."""
    name: str = "paper_outline"
    description: str = "Fetch high level ouline from the paper."
    args_schema: Type[BaseModel] = PaperInput
    
    # Paper-specific config (set at runtime)
    paper_id: str = ""
    
    def __init__(self):
        super().__init__()
    
    def _run(self, paper_id: str) -> str:
        """
        Execute the paper outline search.
        Returns paper outline.
        """
        db = SessionLocal()
        result = db.get(PaperStructure, paper_id)
        if result:
            return result.outline
        else:
            return "No outline found."
