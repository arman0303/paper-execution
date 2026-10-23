import json
from typing import List, Dict, Set, Any, Optional
from app.config import settings
from app.knowledge_base.vector_store import VectorStoreManager
from app.schemas.query_understanding import QueryUnderstandingResult
from app.schemas.documentation import TableDocumentation
from app.schemas.retrieval import RetrievedTableCandidate

class TableDocumentationRetriever:
    """
    Module E: Multi-Representation Table Documentation Retrieval.
    Implements the 6 specific query formulations (Z1 to Z6) defined on
    pages 22-23 of arXiv:2506.12234v1.
    """
    def __init__(
        self,
        vector_store: VectorStoreManager,
        docs_library: Optional[Dict[str, TableDocumentation]] = None
    ):
        self.vector_store = vector_store
        self.docs_library = docs_library or {}

    def retrieve_tables(
        self,
        query_analysis: QueryUnderstandingResult,
        top_n: Optional[int] = None
    ) -> List[RetrievedTableCandidate]:
        n = top_n or settings.TABLE_RETRIEVAL_TOP_N

        norm_q = query_analysis.normalized_question
        main_c = query_analysis.main_clause
        concepts = " ".join([e.label for e in query_analysis.requested_entities])
        if not concepts:
            concepts = norm_q

        # The 6 exact queries Z1..Z6 from paper p. 22-23:
        queries = [
            # Z1: Main clause matching descriptions & entities
            {"name": "Z1", "text": main_c, "filter": ["description", "entity"]},
            # Z2: Normalized question matching descriptions & entities
            {"name": "Z2", "text": norm_q, "filter": ["description", "entity"]},
            # Z3: Extracted concepts matching connected tables & entities
            {"name": "Z3", "text": concepts, "filter": ["connected_tables", "entity"]},
            # Z4: Main clause matching table names
            {"name": "Z4", "text": main_c, "filter": ["table_name"]},
            # Z5: Normalized question matching table names
            {"name": "Z5", "text": norm_q, "filter": ["table_name"]},
            # Z6: Extracted concepts matching table names
            {"name": "Z6", "text": concepts, "filter": ["table_name"]},
        ]

        candidate_map: Dict[str, RetrievedTableCandidate] = {}

        for q in queries:
            results = self.vector_store.query_table_docs(
                query_text=q["text"],
                category_filter=q["filter"],
                top_k=n
            )
            for item in results:
                meta = item["metadata"]
                tbl_name = meta.get("table_name")
                if not tbl_name:
                    continue

                if tbl_name not in candidate_map:
                    conn_tables = []
                    if "connected_tables" in meta:
                        try:
                            conn_tables = json.loads(meta["connected_tables"]) if isinstance(meta["connected_tables"], str) else meta["connected_tables"]
                        except Exception:
                            conn_tables = [meta["connected_tables"]]

                    candidate_map[tbl_name] = RetrievedTableCandidate(
                        table_name=tbl_name,
                        dependencies=meta.get("dependencies", ""),
                        connected_tables=conn_tables,
                        score=item["similarity"],
                        matched_by_queries=[q["name"]]
                    )
                else:
                    # Update score if higher, add query tag
                    if item["similarity"] > candidate_map[tbl_name].score:
                        candidate_map[tbl_name].score = item["similarity"]
                    if q["name"] not in candidate_map[tbl_name].matched_by_queries:
                        candidate_map[tbl_name].matched_by_queries.append(q["name"])

        # Return sorted by relevance score
        candidates = list(candidate_map.values())
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates
