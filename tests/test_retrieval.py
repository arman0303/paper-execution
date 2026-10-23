import pytest
from app.embeddings.sentence_transformer import EmbeddingService
from app.retrieval.progressive_example import ProgressiveExampleRetriever
from app.retrieval.table_retrieval import TableDocumentationRetriever
from app.schemas.query_understanding import QueryUnderstandingResult

def test_paper_similarity_formula():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    # Identical vectors: cos(theta) = 1.0 -> (1 + 1) / 2 = 1.0
    assert abs(EmbeddingService.paper_similarity(v1, v2) - 1.0) < 1e-5

    # Orthogonal vectors: cos(theta) = 0.0 -> (0 + 1) / 2 = 0.5
    v3 = [0.0, 1.0, 0.0]
    assert abs(EmbeddingService.paper_similarity(v1, v3) - 0.5) < 1e-5

def test_progressive_retriever_exact_match(indexing_pipeline):
    retriever = ProgressiveExampleRetriever(
        vector_store=indexing_pipeline.vector_store,
        examples_library=indexing_pipeline.train_examples
    )
    analysis = QueryUnderstandingResult(
        original_question="Show all active customers located in the USA.",
        normalized_question="List active customers in a specific country",
        main_clause="list active customers"
    )
    res = retriever.retrieve(analysis)
    assert res.is_direct_match is True
    assert res.direct_sql is not None

def test_table_retriever_six_queries(indexing_pipeline):
    retriever = TableDocumentationRetriever(
        vector_store=indexing_pipeline.vector_store,
        docs_library=indexing_pipeline.table_docs
    )
    analysis = QueryUnderstandingResult(
        original_question="What is the total revenue?",
        normalized_question="Calculate gross completed order revenue",
        main_clause="calculate revenue"
    )
    candidates = retriever.retrieve_tables(analysis, top_n=5)
    assert len(candidates) > 0
    cand_names = [c.table_name for c in candidates]
    assert "orders" in cand_names or "payments" in cand_names
