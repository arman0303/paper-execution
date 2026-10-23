from app.schemas.sql import SQLGenerationStrategy
from app.schemas.retrieval import RetrievalStage, ExampleRetrievalResult

def determine_generation_strategy(
    example_retrieval_result: ExampleRetrievalResult
) -> SQLGenerationStrategy:
    """
    Selects the SQL generation strategy according to retrieval stage and confidence
    as described in arXiv:2506.12234v1 (p. 26).
    """
    if example_retrieval_result.is_direct_match and example_retrieval_result.direct_sql:
        return SQLGenerationStrategy.DIRECT_OUTPUT

    stage = example_retrieval_result.stage_reached

    if stage == RetrievalStage.STAGE_2_NORMALIZED_P95:
        return SQLGenerationStrategy.EXACT_EXAMPLE
    elif stage in (RetrievalStage.STAGE_3_MAIN_CLAUSE_P99, RetrievalStage.STAGE_5_RERANKED):
        return SQLGenerationStrategy.STRONGLY_ALIGNED
    else:
        return SQLGenerationStrategy.FLEXIBLE_TEMPLATE
