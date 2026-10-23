import json
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings
from app.schemas.example import NormalizedExample
from app.schemas.retrieval import RetrievalStage, ScoredExample, ExampleRetrievalResult
from app.schemas.query_understanding import QueryUnderstandingResult
from app.knowledge_base.vector_store import VectorStoreManager

class ProgressiveExampleRetriever:
    """
    Module D: Progressive Example Retrieval.
    Implements the 5-stage cascading retrieval architecture with progressive
    similarity thresholds as defined in arXiv:2506.12234v1 (p. 16-21).
    """
    def __init__(
        self,
        vector_store: VectorStoreManager,
        examples_library: Optional[Dict[str, NormalizedExample]] = None
    ):
        self.vector_store = vector_store
        self.examples_library = examples_library or {}

    def retrieve(
        self,
        query_analysis: QueryUnderstandingResult,
        reranker_func: Optional[Any] = None
    ) -> ExampleRetrievalResult:
        raw_q = query_analysis.original_question
        norm_q = query_analysis.normalized_question
        main_c = query_analysis.main_clause

        # ---------------------------------------------------------
        # STAGE 1: Exact Match (Sim(I, Ik) -> 1, paper p. 17)
        # ---------------------------------------------------------
        exact_results = self.vector_store.query_examples(
            query_text=raw_q,
            representation_filter=["initial_question"],
            top_k=3
        )
        for res in exact_results:
            score = res["similarity"]
            meta = res["metadata"]
            ex_id = meta.get("example_id")
            example_obj = self._get_example_obj(ex_id, meta)
            if example_obj:
                is_exact_text = raw_q.strip().lower().rstrip("?.,") == example_obj.question.strip().lower().rstrip("?.,")
                if is_exact_text or score >= 0.999:
                    scored_ex = ScoredExample(
                        example=example_obj,
                        similarity_score=1.0 if is_exact_text else score,
                        matched_representation="initial_question",
                        stage=RetrievalStage.STAGE_1_EXACT
                    )
                    return ExampleRetrievalResult(
                        stage_reached=RetrievalStage.STAGE_1_EXACT,
                        is_direct_match=True,
                        direct_sql=example_obj.sql,
                        matched_examples=[scored_ex],
                        candidate_tables=example_obj.tables
                    )

        # ---------------------------------------------------------
        # STAGE 2: Search based on Normalized Representation (P95)
        # ---------------------------------------------------------
        norm_results = self.vector_store.query_examples(
            query_text=norm_q,
            representation_filter=["normalized_question", "initial_question"],
            top_k=5
        )
        stage2_matches: List[ScoredExample] = []
        for res in norm_results:
            score = res["similarity"]
            if score >= settings.THRESHOLD_NORMALIZED_P95:
                meta = res["metadata"]
                ex_id = meta.get("example_id")
                example_obj = self._get_example_obj(ex_id, meta)
                if example_obj and not any(m.example.id == ex_id for m in stage2_matches):
                    stage2_matches.append(
                        ScoredExample(
                            example=example_obj,
                            similarity_score=score,
                            matched_representation=meta.get("representation_type", "normalized_question"),
                            stage=RetrievalStage.STAGE_2_NORMALIZED_P95
                        )
                    )

        if stage2_matches:
            tables = self._extract_tables_from_examples(stage2_matches)
            return ExampleRetrievalResult(
                stage_reached=RetrievalStage.STAGE_2_NORMALIZED_P95,
                is_direct_match=False,
                matched_examples=stage2_matches,
                candidate_tables=tables
            )

        # ---------------------------------------------------------
        # STAGE 3: Search based on Normalized + Main Clause (P99)
        # ---------------------------------------------------------
        combo_query = f"{norm_q} {main_c}".strip()
        stage3_raw = self.vector_store.query_examples(
            query_text=combo_query,
            representation_filter=["normalized_question", "main_clause", "initial_question"],
            top_k=5
        )
        stage3_matches: List[ScoredExample] = []
        for res in stage3_raw:
            score = res["similarity"]
            if score >= settings.THRESHOLD_MAIN_CLAUSE_P99:
                meta = res["metadata"]
                ex_id = meta.get("example_id")
                example_obj = self._get_example_obj(ex_id, meta)
                if example_obj and not any(m.example.id == ex_id for m in stage3_matches):
                    stage3_matches.append(
                        ScoredExample(
                            example=example_obj,
                            similarity_score=score,
                            matched_representation="normalized_and_main_clause",
                            stage=RetrievalStage.STAGE_3_MAIN_CLAUSE_P99
                        )
                    )

        if stage3_matches:
            tables = self._extract_tables_from_examples(stage3_matches)
            return ExampleRetrievalResult(
                stage_reached=RetrievalStage.STAGE_3_MAIN_CLAUSE_P99,
                is_direct_match=False,
                matched_examples=stage3_matches,
                candidate_tables=tables
            )

        # ---------------------------------------------------------
        # STAGE 4: Search with Expanded Representations (P01)
        # ---------------------------------------------------------
        expanded_raw = self.vector_store.query_examples(
            query_text=norm_q,
            representation_filter=None, # Search all representations
            top_k=8
        )
        stage4_candidates: List[ScoredExample] = []
        for res in expanded_raw:
            score = res["similarity"]
            if score >= settings.THRESHOLD_EXPANDED_P01:
                meta = res["metadata"]
                ex_id = meta.get("example_id")
                example_obj = self._get_example_obj(ex_id, meta)
                if example_obj and not any(m.example.id == ex_id for m in stage4_candidates):
                    stage4_candidates.append(
                        ScoredExample(
                            example=example_obj,
                            similarity_score=score,
                            matched_representation=meta.get("representation_type", "expanded"),
                            stage=RetrievalStage.STAGE_4_EXPANDED_P01
                        )
                    )

        # ---------------------------------------------------------
        # STAGE 5: Cross-Encoder Reranking
        # ---------------------------------------------------------
        if stage4_candidates and reranker_func and settings.ENABLE_RERANKER:
            reranked_matches = reranker_func(raw_q, stage4_candidates, threshold=settings.THRESHOLD_RERANKER)
            if reranked_matches:
                tables = self._extract_tables_from_examples(reranked_matches)
                return ExampleRetrievalResult(
                    stage_reached=RetrievalStage.STAGE_5_RERANKED,
                    is_direct_match=False,
                    matched_examples=reranked_matches,
                    candidate_tables=tables
                )

        # Fallback: return top candidate as template reference
        tables = self._extract_tables_from_examples(stage4_candidates)
        return ExampleRetrievalResult(
            stage_reached=RetrievalStage.STAGE_FALLBACK_TEMPLATE,
            is_direct_match=False,
            matched_examples=stage4_candidates[:3],
            candidate_tables=tables
        )

    def _get_example_obj(self, ex_id: Optional[str], meta: Dict[str, Any]) -> Optional[NormalizedExample]:
        if ex_id and ex_id in self.examples_library:
            return self.examples_library[ex_id]
        if "sql" in meta:
            # Reconstruct from metadata
            tables = []
            if "tables" in meta:
                try:
                    tables = json.loads(meta["tables"]) if isinstance(meta["tables"], str) else meta["tables"]
                except Exception:
                    tables = [meta["tables"]]
            return NormalizedExample(
                id=ex_id or "unknown",
                question=meta.get("initial_question", ""),
                sql=meta.get("sql", ""),
                normalized_question=meta.get("normalized_question", ""),
                main_clause=meta.get("main_clause", ""),
                tables=tables
            )
        return None

    def _extract_tables_from_examples(self, examples: List[ScoredExample]) -> List[str]:
        tables = set()
        for scored in examples:
            for t in scored.example.tables:
                tables.add(t)
        return sorted(list(tables))
