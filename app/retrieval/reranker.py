from typing import List, Optional
from app.config import settings
from app.schemas.retrieval import ScoredExample, RetrievalStage

class CrossEncoderReranker:
    """
    Module D, Stage 5: Cross-Encoder Reranking.
    Jointly encodes (User Query, Example Question) pairs to assess deep semantic equivalence.
    Gracefully falls back to rank preservation if the neural cross-encoder model is not loaded.
    """
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.RERANKER_MODEL_NAME
        self._model = None
        self._disabled = not settings.ENABLE_RERANKER

    def _load_model(self):
        if self._model is None and not self._disabled:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except Exception:
                self._disabled = True

    def rerank(
        self,
        query: str,
        candidates: List[ScoredExample],
        threshold: float = 0.50
    ) -> List[ScoredExample]:
        if not candidates:
            return []

        self._load_model()
        if self._model is not None and not self._disabled:
            pairs = [[query, c.example.question] for c in candidates]
            scores = self._model.predict(pairs)
            reranked = []
            for candidate, score in zip(candidates, scores):
                # Sigmoid / normalize if needed
                norm_score = float(score) if 0.0 <= score <= 1.0 else 1.0 / (1.0 + float(np.exp(-score)))
                if norm_score >= threshold:
                    reranked.append(
                        ScoredExample(
                            example=candidate.example,
                            similarity_score=round(norm_score, 4),
                            matched_representation="cross_encoder",
                            stage=RetrievalStage.STAGE_5_RERANKED
                        )
                    )
            reranked.sort(key=lambda x: x.similarity_score, reverse=True)
            return reranked
        else:
            # Fallback: maintain order and filter by threshold
            return [c for c in candidates if c.similarity_score >= threshold]
