import pytest
from pathlib import Path
from app.database.connection import DatabaseConnectionManager
from app.database.introspection import SchemaIntrospector
from app.knowledge_base.vector_store import VectorStoreManager
from app.knowledge_base.indexing_pipeline import IndexingPipeline
from app.llm.mock_provider import MockLLMProvider
from app.sql_validation.validator import SQLValidator
from app.sql_validation.executor import SafeSQLExecutor

@pytest.fixture(scope="session")
def db_path():
    p = Path(__file__).resolve().parent.parent / "data" / "sample_ecommerce.db"
    assert p.exists(), f"Sample database {p} must exist. Run data/seed_data.py first."
    return str(p)

@pytest.fixture(scope="session")
def conn_manager(db_path):
    return DatabaseConnectionManager(db_path)

@pytest.fixture(scope="session")
def introspector(conn_manager):
    return SchemaIntrospector(conn_manager)

@pytest.fixture(scope="session")
def mock_llm():
    return MockLLMProvider()

@pytest.fixture(scope="session")
def indexing_pipeline():
    pipeline = IndexingPipeline()
    pipeline.index_all()
    return pipeline

@pytest.fixture(scope="session")
def sql_validator(indexing_pipeline):
    return SQLValidator(allowed_tables=list(indexing_pipeline.table_docs.keys()))

@pytest.fixture(scope="session")
def sql_executor(conn_manager):
    return SafeSQLExecutor(conn_manager)
