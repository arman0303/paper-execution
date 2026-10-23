import time
from typing import Dict, Any, Optional, List
from app.config import settings
from app.database.connection import DatabaseConnectionManager
from app.knowledge_base.vector_store import VectorStoreManager
from app.knowledge_base.indexing_pipeline import IndexingPipeline
from app.query_understanding.analyzer import QueryUnderstandingAnalyzer
from app.retrieval.progressive_example import ProgressiveExampleRetriever
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.table_retrieval import TableDocumentationRetriever
from app.table_refinement.refiner import TableRefiner
from app.sql_generation.strategies import determine_generation_strategy
from app.sql_generation.generator import SQLGenerator
from app.sql_validation.validator import SQLValidator
from app.sql_validation.executor import SafeSQLExecutor
from app.schemas.sql import GeneratedSQLResponse, SQLGenerationStrategy, ValidationStatus
from app.schemas.retrieval import RetrievalStage

class DatricsText2SQLPipeline:
    """
    End-to-End Orchestrator for the Datrics Text2SQL RAG Framework (arXiv:2506.12234v1).
    Coordinates:
    - Query Understanding
    - Progressive Example Retrieval
    - Multi-Representation Table Retrieval
    - Business Rules & LLM Table Refinement
    - Multi-Strategy SQL Generation
    - AST SQL Validation & Safe Read-Only Execution with Bounded Repair
    """
    def __init__(
        self,
        db_path: Optional[str] = None,
        persist_dir: Optional[str] = None
    ):
        self.db_path = db_path or settings.DATABASE_PATH
        self.conn_mgr = DatabaseConnectionManager(self.db_path)

        # Vector Store & Indexing
        self.vector_store = VectorStoreManager(persist_dir or settings.CHROMA_PERSIST_DIRECTORY)
        self.indexing_pipeline = IndexingPipeline(vector_store=self.vector_store)
        self.indexing_pipeline.index_all()

        # Modules
        self.query_analyzer = QueryUnderstandingAnalyzer()
        self.example_retriever = ProgressiveExampleRetriever(
            vector_store=self.vector_store,
            examples_library=self.indexing_pipeline.train_examples
        )
        self.reranker = CrossEncoderReranker()
        self.table_retriever = TableDocumentationRetriever(
            vector_store=self.vector_store,
            docs_library=self.indexing_pipeline.table_docs
        )
        self.table_refiner = TableRefiner(
            business_rules=self.indexing_pipeline.business_rules,
            domain_instructions=self.indexing_pipeline.domain_instructions,
            table_docs=self.indexing_pipeline.table_docs
        )
        self.sql_generator = SQLGenerator(
            table_docs=self.indexing_pipeline.table_docs,
            dialect=settings.DATABASE_DIALECT
        )
        self.sql_validator = SQLValidator(
            allowed_tables=list(self.indexing_pipeline.table_docs.keys())
        )
        self.sql_executor = SafeSQLExecutor(self.conn_mgr)

    def process_query(self, raw_question: str) -> GeneratedSQLResponse:
        diagnostics = {}

        # -------------------------------------------------------------
        # 1. Query Understanding (Module C)
        # -------------------------------------------------------------
        analysis = self.query_analyzer.analyze(raw_question)

        # Ambiguity / Unsupported early boundary check (Paper p. 2)
        if analysis.is_ambiguous or analysis.is_unsupported:
            warning_msg = analysis.clarification_message or "Question is ambiguous or requires external information not present in the database."
            return GeneratedSQLResponse(
                sql="",
                explanation="Clarification requested before query synthesis.",
                strategy_used=SQLGenerationStrategy.FLEXIBLE_TEMPLATE,
                warnings=[warning_msg],
                clarification_requested=warning_msg
            )

        # -------------------------------------------------------------
        # 2. Progressive Example Retrieval (Module D)
        # -------------------------------------------------------------
        example_res = self.example_retriever.retrieve(
            query_analysis=analysis,
            reranker_func=self.reranker.rerank
        )
        strategy = determine_generation_strategy(example_res)

        # -------------------------------------------------------------
        # 3. Table Documentation Retrieval & Refinement (Modules E & F)
        # -------------------------------------------------------------
        refined_tables: List[str] = []
        if strategy == SQLGenerationStrategy.DIRECT_OUTPUT and example_res.direct_sql:
            refined_tables = example_res.candidate_tables
        else:
            # Multi-category 6-query table retrieval
            retrieved_candidates = self.table_retriever.retrieve_tables(analysis)
            t_det = [c.table_name for c in retrieved_candidates]
            t_code = example_res.candidate_tables

            # Two-stage refinement: TB = LLM(N, R), TR = LLM(N, Instr_Domain, R, T_total U T_code)
            refinement_res = self.table_refiner.refine(
                normalized_question=analysis.normalized_question,
                t_det=t_det,
                t_code=t_code
            )
            refined_tables = refinement_res.get("refined_tables", t_det)

        if not refined_tables:
            refined_tables = list(self.indexing_pipeline.table_docs.keys())

        # -------------------------------------------------------------
        # 4. SQL Generation & Bounded Correction Loop (Modules G & H)
        # -------------------------------------------------------------
        max_attempts = settings.MAX_SQL_CORRECTION_ATTEMPTS
        attempt = 0
        last_error = None
        response: Optional[GeneratedSQLResponse] = None

        while attempt <= max_attempts:
            response = self.sql_generator.generate(
                question=raw_question,
                normalized_question=analysis.normalized_question,
                strategy=strategy,
                refined_tables=refined_tables,
                examples=example_res.matched_examples,
                business_rules=self.indexing_pipeline.business_rules,
                direct_sql=example_res.direct_sql if strategy == SQLGenerationStrategy.DIRECT_OUTPUT else None,
                correction_error=last_error
            )

            # Step 5: AST Validation
            val_result = self.sql_validator.validate(response.sql)
            response.validation = val_result

            if val_result.is_valid:
                # Step 6: Safe Read-only Execution
                exec_result = self.sql_executor.execute(response.sql)
                response.execution = exec_result
                if exec_result.success:
                    break
                else:
                    # Execution failed, feed back to repair loop
                    last_error = exec_result.error_message
                    attempt += 1
            else:
                # Validation failed, feed back to repair loop
                last_error = val_result.error_message
                attempt += 1

        return response
