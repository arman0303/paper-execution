from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.example import NormalizedExample

class RetrievalStage(str, Enum):
    STAGE_1_EXACT = "STAGE_1_EXACT"
    STAGE_2_NORMALIZED_P95 = "STAGE_2_NORMALIZED_P95"
    STAGE_3_MAIN_CLAUSE_P99 = "STAGE_3_MAIN_CLAUSE_P99"
    STAGE_4_EXPANDED_P01 = "STAGE_4_EXPANDED_P01"
    STAGE_5_RERANKED = "STAGE_5_RERANKED"
    STAGE_FALLBACK_TEMPLATE = "STAGE_FALLBACK_TEMPLATE"

class ScoredExample(BaseModel):
    """Retrieved candidate example paired with its similarity metric."""
    example: NormalizedExample
    similarity_score: float
    matched_representation: str
    stage: RetrievalStage

class ExampleRetrievalResult(BaseModel):
    """Outcome of progressive example retrieval."""
    stage_reached: RetrievalStage
    is_direct_match: bool = False
    direct_sql: Optional[str] = None
    matched_examples: List[ScoredExample] = Field(default_factory=list)
    candidate_tables: List[str] = Field(default_factory=list)

class RetrievedTableCandidate(BaseModel):
    """Table documentation candidate retrieved via ChromaDB multi-category query."""
    table_name: str
    dependencies: Optional[str] = None
    connected_tables: List[str] = Field(default_factory=list)
    score: float = 0.0
    matched_by_queries: List[str] = Field(default_factory=list)
