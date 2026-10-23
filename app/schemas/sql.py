from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class SQLGenerationStrategy(str, Enum):
    DIRECT_OUTPUT = "DIRECT_OUTPUT"                      # S_sql^R: Exact match from stored examples
    EXACT_EXAMPLE = "EXACT_EXAMPLE"                      # S_code^**: Near-identical pattern from example
    STRONGLY_ALIGNED = "STRONGLY_ALIGNED"                # S_code^*: Highly relevant example structure + schema
    FLEXIBLE_TEMPLATE = "FLEXIBLE_TEMPLATE"              # S_code + TR: Broad table documentation + template guidance
    BASELINE_SCHEMA_ONLY = "BASELINE_SCHEMA_ONLY"        # Baseline without retrieval for empirical comparison

class ValidationStatus(str, Enum):
    VALID = "VALID"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    DISALLOWED_OPERATION = "DISALLOWED_OPERATION"
    NONEXISTENT_IDENTIFIER = "NONEXISTENT_IDENTIFIER"
    EXECUTION_ERROR = "EXECUTION_ERROR"

class ValidationResult(BaseModel):
    is_valid: bool
    status: ValidationStatus
    error_message: Optional[str] = None
    parsed_tables: List[str] = Field(default_factory=list)
    parsed_columns: List[str] = Field(default_factory=list)

class ExecutionResult(BaseModel):
    success: bool
    row_count: int = 0
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0

class GeneratedSQLResponse(BaseModel):
    sql: str
    explanation: str
    strategy_used: SQLGenerationStrategy
    referenced_tables: List[str] = Field(default_factory=list)
    referenced_columns: List[str] = Field(default_factory=list)
    filters_applied: List[str] = Field(default_factory=list)
    aggregations_applied: List[str] = Field(default_factory=list)
    relevant_examples_used: List[str] = Field(default_factory=list)
    validation: Optional[ValidationResult] = None
    execution: Optional[ExecutionResult] = None
    warnings: List[str] = Field(default_factory=list)
    clarification_requested: Optional[str] = None
