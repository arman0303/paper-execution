from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ExtractedEntity(BaseModel):
    """
    Extracted entity Ek = {(Li, Ki, Ji)}:
    - Li: label of entity
    - Ki: type (category, metric, identifier)
    - Ji: additional attributes
    """
    label: str
    entity_type: Literal["category", "metric", "identifier"] = "category"
    attributes: Optional[str] = None

class DataSourceReference(BaseModel):
    """Data source Vk = {Tik, Cik} identifying tables and columns."""
    table: str
    columns: List[str] = Field(default_factory=list)

class QueryOperation(BaseModel):
    """Query operation O = {(operation, target, condition)}."""
    operation: str = Field(description="e.g. FILTER, SUM, AVG, COUNT, GROUP BY, ORDER BY, LIMIT, JOIN")
    target: str = Field(description="Target column, table, or expression")
    condition: Optional[str] = Field(default=None, description="Human readable filter or condition")

class NormalizedExample(BaseModel):
    """
    Stored Question-SQL example Ak = (Ik, Scodek, Nk, Mk, Ek, Vk, Ok).
    """
    id: str
    question: str = Field(description="Ik: Initial user query")
    sql: str = Field(description="Scodek: Corresponding ground-truth SQL query")
    normalized_question: str = Field(description="Nk: Normalized form of the initial question")
    main_clause: str = Field(description="Mk: Main clause representing primary data request")
    details: Optional[str] = Field(default="", description="M'k: Details and constraints expanding the main clause")
    entities: List[ExtractedEntity] = Field(default_factory=list, description="Ek: Extracted entities")
    tables: List[str] = Field(default_factory=list, description="Tik: Referenced database tables")
    columns: List[str] = Field(default_factory=list, description="Cik: Referenced table columns")
    operations: List[QueryOperation] = Field(default_factory=list, description="Ok: Identified operations")
    variations: List[str] = Field(
        default_factory=list,
        description="3 generated question variations for multi-embedding representation"
    )
