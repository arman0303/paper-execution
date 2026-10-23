import json
import re
from typing import List, Dict, Any, Optional
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.schemas.sql import SQLGenerationStrategy, GeneratedSQLResponse
from app.schemas.documentation import TableDocumentation
from app.schemas.retrieval import ScoredExample

class SQLGenerator:
    """
    Module G: Multi-Strategy SQL Generation Engine.
    Executes synthesis according to the 4 paper strategies:
    - Direct Output (S_sql^R)
    - Exact Example-Driven (S_code^**)
    - Strongly Aligned Example-Driven (S_code^*)
    - Flexible Template / Documentation-Driven (S_code + TR)
    Supports schema injection, business rules enforcement, and bounded correction.
    """
    def __init__(
        self,
        table_docs: Optional[Dict[str, TableDocumentation]] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        dialect: str = "sqlite"
    ):
        self.table_docs = table_docs or {}
        self.llm = llm_provider or get_llm_provider()
        self.dialect = dialect

    def generate(
        self,
        question: str,
        normalized_question: str,
        strategy: SQLGenerationStrategy,
        refined_tables: List[str],
        examples: List[ScoredExample],
        business_rules: Optional[List[Dict[str, Any]]] = None,
        direct_sql: Optional[str] = None,
        correction_error: Optional[str] = None
    ) -> GeneratedSQLResponse:

        # Strategy 1: Direct Output SQL Code
        if strategy == SQLGenerationStrategy.DIRECT_OUTPUT and direct_sql:
            return GeneratedSQLResponse(
                sql=direct_sql.strip(),
                explanation="Directly matched exact question in knowledge base (Stage 1 Exact Match).",
                strategy_used=SQLGenerationStrategy.DIRECT_OUTPUT,
                referenced_tables=refined_tables,
                relevant_examples_used=["Stage 1 Exact Match"]
            )

        # Build schema snippet for refined tables
        schema_lines = []
        for tbl in refined_tables:
            doc = self.table_docs.get(tbl)
            if doc:
                cols_str = ", ".join([f"{c.column}" for c in doc.columns])
                schema_lines.append(f"Table `{tbl}` (columns: {cols_str})")
                if doc.dependencies_thoughts:
                    schema_lines.append(f"  Relationships: {doc.dependencies_thoughts}")
            else:
                schema_lines.append(f"Table `{tbl}`")

        schema_context = "\n".join(schema_lines)

        # Format examples
        example_lines = []
        for idx, ex in enumerate(examples[:3], 1):
            example_lines.append(f"Example {idx}:\n  Question: {ex.example.question}\n  SQL: {ex.example.sql}")
        examples_context = "\n\n".join(example_lines) if example_lines else "No similar examples available."

        # Format business rules
        rules_context = "\n".join([f"- {r.get('rule')}" for r in (business_rules or [])])

        correction_prompt = ""
        if correction_error:
            correction_prompt = f"\nPREVIOUS ATTEMPT FAILED WITH ERROR:\n{correction_error}\nPlease fix the error while maintaining the required business logic.\n"

        prompt = f"""
You are an expert SQL Generator generating standard {self.dialect.upper()} queries.
Synthesize an accurate, performant, and safe SQL query for the following request:

Original Question: "{question}"
Normalized Intent: "{normalized_question}"
Generation Strategy: {strategy.value}

Allowed Database Schema:
{schema_context}

Relevant Business Rules:
{rules_context or "None"}

Retrieved SQL Reference Examples:
{examples_context}
{correction_prompt}
Strict Generation Guidelines:
1. Generate valid {self.dialect.upper()} syntax ONLY.
2. Only SELECT queries are permitted (no INSERT/UPDATE/DELETE/ALTER/PRAGMA).
3. Strictly use ONLY the tables and columns present in the Allowed Database Schema above.
4. Correctly join tables using verified primary key / foreign key relations.
5. Apply business rule conditions (e.g., status = 'completed' for revenue calculation).

Return ONLY a JSON object with this exact schema:
{{
    "sql": "SELECT ...",
    "explanation": "Clear plain English explanation of what the query does and how joins/filters were chosen.",
    "referenced_tables": ["table1", "table2"],
    "referenced_columns": ["col1", "col2"],
    "filters_applied": ["filter1"],
    "aggregations_applied": ["SUM"],
    "warnings": []
}}
"""
        response_text = self.llm.generate(prompt=prompt, json_mode=True, temperature=0.0)

        try:
            cleaned = re.sub(r"^```json\s*", "", response_text.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)

            sql = data.get("sql", "").strip()
            # Clean possible markdown sql blocks in string
            sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
            sql = re.sub(r"```$", "", sql).strip()

            return GeneratedSQLResponse(
                sql=sql,
                explanation=data.get("explanation", ""),
                strategy_used=strategy,
                referenced_tables=data.get("referenced_tables", refined_tables),
                referenced_columns=data.get("referenced_columns", []),
                filters_applied=data.get("filters_applied", []),
                aggregations_applied=data.get("aggregations_applied", []),
                relevant_examples_used=[ex.example.id for ex in examples],
                warnings=data.get("warnings", [])
            )
        except Exception:
            # Fallback to direct example SQL if available
            fallback_sql = examples[0].example.sql if examples else "SELECT 1;"
            return GeneratedSQLResponse(
                sql=fallback_sql,
                explanation="Generated using template fallback.",
                strategy_used=strategy,
                referenced_tables=refined_tables,
                relevant_examples_used=[ex.example.id for ex in examples]
            )
