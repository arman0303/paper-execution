import math
from typing import List, Union
import numpy as np
from app.config import settings

class EmbeddingService:
    """
    Embedding service supporting SentenceTransformers with normalized vectors
    and the paper's cosine similarity formula: Sim(X, Y) = (cos(theta) + 1) / 2
    """
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._model = None
        self._use_fallback = False

    def _load_model(self):
        if settings.EMBEDDING_PROVIDER.lower() in ("tfidf", "fallback", "hash"):
            self._use_fallback = True
            return

        if self._model is None and not self._use_fallback:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                # Graceful fallback to word-vector/TF-IDF hashing if model download is offline
                self._use_fallback = True

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        self._load_model()
        if self._model is not None and not self._use_fallback:
            embeddings = self._model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()
        else:
            # Deterministic word-frequency embedding fallback (384-dimensional hashed representation)
            return [self._hash_fallback_embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]

    def _hash_fallback_embed(self, text: str, dim: int = 384) -> List[float]:
        """Deterministic normalized pseudo-embedding for offline/test environments."""
        vec = np.zeros(dim, dtype=np.float32)
        words = text.lower().split()
        if not words:
            return vec.tolist()
        for i, word in enumerate(words):
            h = hash(word) % dim
            vec[h] += 1.0 / (i + 1)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @staticmethod
    def paper_similarity(vec_a: Union[List[float], np.ndarray], vec_b: Union[List[float], np.ndarray]) -> float:
        """
        Paper Cosine Similarity Formula (arXiv:2506.12234v1, p. 16):
        Sim(X, Yi) = (cos(theta) + 1) / 2 = (X·Yi + ||X|| ||Yi||) / (2 ||X|| ||Yi||)
        Yields normalized score in [0.0, 1.0].
        """
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        cos_theta = float(np.dot(a, b) / (norm_a * norm_b))
        # Clamp to [-1.0, 1.0] for floating point precision
        cos_theta = max(-1.0, min(1.0, cos_theta))
        return (cos_theta + 1.0) / 2.0
