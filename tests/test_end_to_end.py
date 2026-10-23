import pytest
from app.pipeline import DatricsText2SQLPipeline
from app.schemas.sql import SQLGenerationStrategy

def test_pipeline_end_to_end_exact_query():
    pipeline = DatricsText2SQLPipeline()
    response = pipeline.process_query("Show all active customers located in the USA.")
    assert response.sql is not None
    assert "customers" in response.sql.lower()
    assert response.validation.is_valid is True
    assert response.execution.success is True
    assert response.execution.row_count > 0

def test_pipeline_end_to_end_aggregation():
    pipeline = DatricsText2SQLPipeline()
    response = pipeline.process_query("What is the total revenue generated from completed orders?")
    assert response.sql is not None
    assert "orders" in response.sql.lower()
    assert response.validation.is_valid is True
    assert response.execution.success is True

def test_pipeline_clarification_on_ambiguity():
    pipeline = DatricsText2SQLPipeline()
    response = pipeline.process_query("Show me top subscribers")
    assert response.clarification_requested is not None
    assert len(response.warnings) > 0
