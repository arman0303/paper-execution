import pytest
from app.query_understanding.analyzer import QueryUnderstandingAnalyzer

def test_query_understanding_normalizes_directive():
    analyzer = QueryUnderstandingAnalyzer()
    res = analyzer.analyze("Show all active customers in the USA.")
    assert res.is_ambiguous is False
    assert len(res.normalized_question) > 0
    assert len(res.main_clause) > 0

def test_query_understanding_detects_ambiguity():
    analyzer = QueryUnderstandingAnalyzer()
    res = analyzer.analyze("Show me top subscribers")
    assert res.is_ambiguous is True
    assert res.clarification_message is not None

def test_query_understanding_detects_unsupported():
    analyzer = QueryUnderstandingAnalyzer()
    res = analyzer.analyze("Predict the sales forecast for next quarter using linear regression.")
    assert res.is_unsupported is True
