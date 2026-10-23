import json
import re
from typing import List, Dict, Any, Optional, Set
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.schemas.documentation import TableDocumentation

class TableRefiner:
    """
    Module F: Domain-Specific Table Refinement.
    Implements two-stage refinement from arXiv:2506.12234v1 (p. 24-25):
    1. TB = LLM(N, R) - Business rules table detection.
    2. TR = LLM(N, Instr_Domain, R, T_total U T_code) - Reasoning-based refinement.
    """
    def __init__(
        self,
        business_rules: Optional[List[Dict[str, Any]]] = None,
        domain_instructions: str = "",
        table_docs: Optional[Dict[str, TableDocumentation]] = None,
        llm_provider: Optional[BaseLLMProvider] = None
    ):
        self.business_rules = business_rules or []
        self.domain_instructions = domain_instructions
        self.table_docs = table_docs or {}
        self.llm = llm_provider or get_llm_provider()

    def refine_with_business_rules(self, normalized_question: str) -> List[str]:
        """Stage 1: TB = LLM(N, R)"""
        if not self.business_rules:
            return []

        rules_str = "\n".join([f"- {r.get('name')}: {r.get('rule')}" for r in self.business_rules])
        prompt = f"""
Given the normalized user question and domain business rules, identify any additional database tables that are strictly required by business logic.

Normalized Question: "{normalized_question}"

Business Rules:
{rules_str}

Return a JSON object:
{{
    "tables": ["table1", "table2"],
    "reasoning": "brief justification"
}}
"""
        response = self.llm.generate(prompt=prompt, json_mode=True, temperature=0.0)
        try:
            cleaned = re.sub(r"^```json\s*", "", response.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            return data.get("tables", [])
        except Exception:
            return []

    def final_table_refinement(
        self,
        normalized_question: str,
        candidate_tables: List[str]
    ) -> Dict[str, Any]:
        """
        Stage 2: TR = LLM(N, Instr_Domain, R, T_total U T_code)
        Analyzes table coverage, dependencies/joins, and business constraints.
        """
        # Build schema snippet for candidate tables
        cand_schemas = []
        for tbl in candidate_tables:
            doc = self.table_docs.get(tbl)
            if doc:
                cols = ", ".join([f"{c.column} ({c.description})" for c in doc.columns[:5]])
                cand_schemas.append(f"Table `{tbl}`:\n  Summary: {doc.summary}\n  Keys: {doc.keys}\n  Connected: {doc.connected_tables}\n  Columns: {cols}")
            else:
                cand_schemas.append(f"Table `{tbl}` (candidate)")

        schema_context = "\n\n".join(cand_schemas)
        rules_str = "\n".join([f"- {r.get('rule')}" for r in self.business_rules])

        prompt = f"""
You are the Table Refinement engine of the Datrics Text2SQL system.
Analyze the candidate tables and determine the exact, minimal, and fully-connected set of tables (TR) needed to answer the question.

Normalized Question: "{normalized_question}"

Candidate Tables Context:
{schema_context}

Domain-Specific Instructions (Instr_Domain):
{self.domain_instructions or "Follow standard foreign key relationships."}

Business Rules:
{rules_str or "None specified."}

Refinement Requirements:
1. Table Coverage Analysis: Verify which tables contain the target data points.
2. Comprehensive Join Coverage: Include necessary bridge/junction tables to form valid join paths.
3. Eliminate Unnecessary Tables: Exclude tables not needed to answer the question.

Return a JSON object:
{{
    "refined_tables": ["table1", "table2"],
    "justifications": {{
        "table1": "Why table1 is required",
        "table2": "Why table2 is required"
    }},
    "join_plan": "Explanation of joins between selected tables"
}}
"""
        response = self.llm.generate(prompt=prompt, json_mode=True, temperature=0.0)
        try:
            cleaned = re.sub(r"^```json\s*", "", response.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            refined = data.get("refined_tables", candidate_tables)
            return {
                "refined_tables": refined,
                "justifications": data.get("justifications", {}),
                "join_plan": data.get("join_plan", "")
            }
        except Exception:
            return {
                "refined_tables": candidate_tables,
                "justifications": {t: "Selected via retrieval" for t in candidate_tables},
                "join_plan": ""
            }

    def refine(
        self,
        normalized_question: str,
        t_det: List[str],
        t_code: List[str]
    ) -> Dict[str, Any]:
        """
        Executes end-to-end refinement:
        T_total = T_det U TB
        TR = LLM(N, Instr_Domain, R, T_total U T_code)
        """
        tb = self.refine_with_business_rules(normalized_question)
        t_total = list(set(t_det).union(set(tb)))
        all_candidates = list(set(t_total).union(set(t_code)))

        if not all_candidates:
            all_candidates = list(self.table_docs.keys())

        return self.final_table_refinement(normalized_question, all_candidates)
