from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.example import ExtractedEntity, QueryOperation

class QueryUnderstandingResult(BaseModel):
    """
    Validated structured representation extracted from incoming natural-language user query.
    """
    original_question: str
    normalized_question: str
    main_clause: str
    details: Optional[str] = ""
    requested_entities: List[ExtractedEntity] = Field(default_factory=list)
    relevant_metrics: List[str] = Field(default_factory=list)
    relevant_dimensions: List[str] = Field(default_factory=list)
    candidate_tables: List[str] = Field(default_factory=list)
    candidate_columns: List[str] = Field(default_factory=list)
    operations: List[QueryOperation] = Field(default_factory=list)
    is_ambiguous: bool = False
    is_unsupported: bool = False
    clarification_message: Optional[str] = None
