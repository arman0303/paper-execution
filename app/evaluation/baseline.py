import json
import re
from typing import Dict, Any, List, Optional
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.schemas.sql import GeneratedSQLResponse, SQLGenerationStrategy
from app.schemas.documentation import TableDocumentation

class SchemaOnlyBaselineGenerator:
    """
    Baseline comparison system: Generates SQL using the database schema alone,
    without example retrieval, without progressive matching, and without domain instruction extraction.
    """
    def __init__(
        self,
        table_docs: Dict[str, TableDocumentation],
        llm_provider: Optional[BaseLLMProvider] = None,
        dialect: str = "sqlite"
    ):
        self.table_docs = table_docs
        self.llm = llm_provider or get_llm_provider()
        self.dialect = dialect

    def generate(self, question: str) -> GeneratedSQLResponse:
        # Provide full schema without any example guidance
        schema_lines = []
        for tbl, doc in self.table_docs.items():
            cols = ", ".join([c.column for c in doc.columns])
            schema_lines.append(f"Table {tbl} ({cols})")
        schema_context = "\n".join(schema_lines)

        prompt = f"""
You are an AI generating standard {self.dialect.upper()} SQL queries.
Schema:
{schema_context}

Question: "{question}"

Synthesize a single valid SELECT query.
Return ONLY a JSON object:
{{
    "sql": "SELECT ...",
    "explanation": "...",
    "referenced_tables": ["table1"]
}}
"""
        response_text = self.llm.generate(prompt=prompt, json_mode=True, temperature=0.0)
        try:
            cleaned = re.sub(r"^```json\s*", "", response_text.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            sql = data.get("sql", "").strip()
            sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
            sql = re.sub(r"```$", "", sql).strip()

            return GeneratedSQLResponse(
                sql=sql,
                explanation=data.get("explanation", "Baseline generation"),
                strategy_used=SQLGenerationStrategy.BASELINE_SCHEMA_ONLY,
                referenced_tables=data.get("referenced_tables", [])
            )
        except Exception:
            return GeneratedSQLResponse(
                sql="SELECT 1;",
                explanation="Baseline failed",
                strategy_used=SQLGenerationStrategy.BASELINE_SCHEMA_ONLY,
                referenced_tables=[]
            )
