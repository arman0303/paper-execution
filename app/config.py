from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # LLM Settings
    LLM_PROVIDER: str = "mock"  # "mock", "gemini", "openai"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Embeddings & Vector DB
    EMBEDDING_PROVIDER: str = "sentence-transformers" # "sentence-transformers", "tfidf"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHROMA_PERSIST_DIRECTORY: str = str(BASE_DIR / "chroma_storage")
    ENABLE_RERANKER: bool = False
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Database
    DATABASE_PATH: str = str(BASE_DIR / "data" / "sample_ecommerce.db")
    DATABASE_DIALECT: str = "sqlite"

    # Progressive Retrieval Thresholds (Mapped to paper empirical findings)
    THRESHOLD_EXACT_MATCH: float = 0.98       # Sim(I, Ik) -> 1
    THRESHOLD_NORMALIZED_P95: float = 0.92    # P95 for normalized questions
    THRESHOLD_MAIN_CLAUSE_P99: float = 0.88   # P99 for normalized + main clause
    THRESHOLD_EXPANDED_P01: float = 0.75      # P01 for expanded search
    THRESHOLD_RERANKER: float = 0.50          # tau' threshold for cross-encoder reranker

    # Algorithm settings
    ENTITY_VOTING_ROUNDS: int = 3
    ENTITY_VOTING_MIN_FREQUENCY: int = 2
    PARAPHRASE_COUNT: int = 3
    TABLE_RETRIEVAL_TOP_N: int = 10           # ni = 10 from paper p. 23
    MAX_EXECUTION_TIMEOUT_SECONDS: float = 5.0
    MAX_EXECUTION_ROWS: int = 100
    MAX_SQL_CORRECTION_ATTEMPTS: int = 2

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
