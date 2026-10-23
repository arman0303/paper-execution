import re
import json
from typing import Optional, List, Dict, Any
from app.schemas.query_understanding import QueryUnderstandingResult
from app.schemas.example import ExtractedEntity, QueryOperation
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider

class QueryUnderstandingAnalyzer:
    """
    Module C: Query Understanding.
    Transforms raw user query into validated structured representation:
    Nk (Normalized), Mk (Main Clause), M'k (Details), Ek (Entities),
    metrics, dimensions, candidate tables/columns, operations, and ambiguity checks.
    """
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()

    def analyze(self, raw_query: str) -> QueryUnderstandingResult:
        prompt = f"""
You are the Query Understanding module of the Datrics Text2SQL system.
Analyze the following natural-language user query for an e-commerce database with tables:
[customers, products, orders, order_items, payments].

User Query: "{raw_query}"

Follow the Datrics normalization and structuring rules:
1. Normalize the question (Nk):
   - Remove database-specific names (table/column names).
   - Remove display instructions (e.g. 'show', 'display', 'get', 'give me').
   - Generalize conditions (e.g. 'in May 2024' -> 'for a specified time range', 'greater than 100' -> 'above a numerical threshold').
   - Maintain directive form (e.g. 'Show sales data' -> 'Sales data').
2. Extract Main Clause (Mk):
   - Primary data request retaining essential meaning, excluding non-critical filters/modifiers.
3. Extract Details (M'k):
   - Auxiliary conditions, time frames, grouping, ordering constraints.
4. Extract Requested Entities:
   - Identify core concepts, label, type ('category', 'metric', 'identifier').
5. Identify Ambiguity or Unsupported Requests:
   - If ambiguous (such as vague rankings lacking clear criteria), set is_ambiguous=True and formulate a clarification_message.
   - If unsupported (such as machine learning forecasting or tables not in schema), set is_unsupported=True.

Return ONLY a JSON object with this exact schema:
{{
    "original_question": "{raw_query}",
    "normalized_question": "...",
    "main_clause": "...",
    "details": "...",
    "requested_entities": [
        {{"label": "...", "entity_type": "category|metric|identifier", "attributes": "..."}}
    ],
    "relevant_metrics": ["..."],
    "relevant_dimensions": ["..."],
    "candidate_tables": ["..."],
    "candidate_columns": ["..."],
    "operations": [
        {{"operation": "FILTER|SUM|AVG|COUNT|GROUP BY|ORDER BY|JOIN", "target": "...", "condition": "..."}}
    ],
    "is_ambiguous": false,
    "is_unsupported": false,
    "clarification_message": null
}}
"""
        response_text = self.llm.generate(prompt=prompt, json_mode=True, temperature=0.0)

        try:
            # Clean markdown code block wraps if present
            cleaned = re.sub(r"^```json\s*", "", response_text.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)

            entities = [
                ExtractedEntity(
                    label=e.get("label", ""),
                    entity_type=e.get("entity_type", "category"),
                    attributes=e.get("attributes")
                )
                for e in data.get("requested_entities", [])
            ]

            operations = [
                QueryOperation(
                    operation=op.get("operation", "SELECT"),
                    target=op.get("target", "*"),
                    condition=op.get("condition")
                )
                for op in data.get("operations", [])
            ]

            return QueryUnderstandingResult(
                original_question=raw_query,
                normalized_question=data.get("normalized_question") or raw_query,
                main_clause=data.get("main_clause") or raw_query,
                details=data.get("details", ""),
                requested_entities=entities,
                relevant_metrics=data.get("relevant_metrics", []),
                relevant_dimensions=data.get("relevant_dimensions", []),
                candidate_tables=data.get("candidate_tables", []),
                candidate_columns=data.get("candidate_columns", []),
                operations=operations,
                is_ambiguous=bool(data.get("is_ambiguous", False)),
                is_unsupported=bool(data.get("is_unsupported", False)),
                clarification_message=data.get("clarification_message")
            )
        except Exception:
            # Deterministic fallback normalization using regex heuristics
            norm = re.sub(r"^(show|display|get|list|find|give me)\s+", "", raw_query, flags=re.IGNORECASE).strip()
            return QueryUnderstandingResult(
                original_question=raw_query,
                normalized_question=norm,
                main_clause=norm,
                details="",
                requested_entities=[ExtractedEntity(label=norm, entity_type="category")],
                candidate_tables=[],
                operations=[]
            )
