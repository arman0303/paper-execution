import json
import re
from typing import Dict, Any, List, Optional
from app.schemas.documentation import TableDocumentation, ColumnDescription
from app.database.introspection import SchemaIntrospector
from app.ingestion.entity_voting import EntityVotingExtractor
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider

class TableDocGenerator:
    """
    Module A: Generates structured table documentation from database schema introspection
    and LLM processing.
    """
    def __init__(
        self,
        schema_introspector: SchemaIntrospector,
        llm_provider: Optional[BaseLLMProvider] = None
    ):
        self.introspector = schema_introspector
        self.llm = llm_provider or get_llm_provider()
        self.voting_extractor = EntityVotingExtractor(self.llm)

    def generate_documentation_for_table(self, table_name: str) -> TableDocumentation:
        table_info = self.introspector.inspect_table_schema(table_name)
        col_names = [c["name"] for c in table_info["columns"]]
        col_text = ", ".join(col_names)
        fk_text = ", ".join([f"{fk['from_column']} -> {fk['to_table']}.{fk['to_column']}" for fk in table_info["foreign_keys"]])

        prompt = f"""
You are documenting a relational database table for a Text-to-SQL system.
Table Name: {table_name}
Columns: {col_text}
Foreign Keys: {fk_text or "None"}

Generate structured JSON documentation adhering to this schema:
{{
    "name": "{table_name}",
    "summary": "Brief 1-line description of what table contains",
    "purpose": "Detailed explanation of role and why it exists",
    "dependencies_thoughts": "Informal notes on relationships with other tables",
    "keys": {json.dumps(table_info["primary_keys"])},
    "connected_tables": {json.dumps(table_info["connected_tables"])},
    "columns": [
        {{"column": "col_name", "description": "functional description"}}
    ]
}}
"""
        response = self.llm.generate(prompt=prompt, json_mode=True, temperature=0.0)
        try:
            cleaned = re.sub(r"^```json\s*", "", response.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
        except Exception:
            data = {
                "name": table_name,
                "summary": f"Table storing {table_name} records.",
                "purpose": f"Tracks {table_name} data in relational structure.",
                "dependencies_thoughts": f"Connected to {table_info['connected_tables']}",
                "keys": table_info["primary_keys"],
                "connected_tables": table_info["connected_tables"],
                "columns": [{"column": c["name"], "description": f"Field {c['name']} of type {c['type']}"} for c in table_info["columns"]]
            }

        # Step 2: Entity Voting Extraction
        all_entities, strong_entities = self.voting_extractor.extract_with_voting(
            table_name=table_name,
            table_summary=data.get("summary", ""),
            columns_text=col_text
        )

        columns_objs = [
            ColumnDescription(
                column=col["column"],
                description=col.get("description", "")
            )
            for col in data.get("columns", [])
        ]

        return TableDocumentation(
            name=table_name,
            summary=data.get("summary", ""),
            purpose=data.get("purpose", ""),
            dependencies_thoughts=data.get("dependencies_thoughts", ""),
            keys=data.get("keys", table_info["primary_keys"]),
            connected_tables=data.get("connected_tables", table_info["connected_tables"]),
            columns=columns_objs,
            entities=all_entities,
            strong_entities=strong_entities
        )
