from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ColumnDescription(BaseModel):
    """Structured column description matching paper specification."""
    column: str = Field(description="Column name")
    description: str = Field(description="Functional meaning and role of column")

class TableDocumentation(BaseModel):
    """
    Table documentation schema matching Datrics paper (arXiv:2506.12234v1, p. 3-7).
    """
    name: str = Field(description="The table's name")
    summary: str = Field(description="A brief description of what the table contains")
    purpose: str = Field(description="Explains the table's role and why it exists")
    dependencies_thoughts: str = Field(
        default="",
        description="Informal notes on relationships between this table's fields and fields in other tables"
    )
    keys: List[str] = Field(
        default_factory=list,
        description="A list of key columns used to join or relate to other tables"
    )
    connected_tables: List[str] = Field(
        default_factory=list,
        description="An array of related table names"
    )
    columns: List[ColumnDescription] = Field(
        default_factory=list,
        description="An array of column objects (name + description)"
    )
    entities: List[str] = Field(
        default_factory=list,
        description="Key concepts extracted from the documentation"
    )
    strong_entities: List[str] = Field(
        default_factory=list,
        description="Subset of entities deemed particularly significant via voting strategy"
    )

class MinorEntityMapping(BaseModel):
    """
    Minor Entity (Em): Specific attributes or discrete data points mapping directly to columns or simple aggregates.
    """
    entity_name: str
    table: str
    column: Optional[str] = None
    aggregation: Optional[str] = None

class MajorEntityMapping(BaseModel):
    """
    Major Entity (EM): Generalized concepts requiring multiple tables or complex relationships.
    """
    entity_name: str
    tables: List[str]
    join_condition: Optional[str] = None
    notes: Optional[str] = None

class DomainKnowledge(BaseModel):
    """
    Structured domain knowledge representing domain-specific entity mappings (Instr_Domain).
    """
    minor_entities: List[MinorEntityMapping] = Field(default_factory=list)
    major_entities: List[MajorEntityMapping] = Field(default_factory=list)
    instructions_text: str = Field(
        default="",
        description="Synthesized markdown instructions for LLM table selection and join generation"
    )
