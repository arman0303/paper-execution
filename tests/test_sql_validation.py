import pytest
from app.schemas.sql import ValidationStatus

def test_valid_select_query_passes(sql_validator):
    sql = "SELECT id, name FROM customers WHERE country = 'USA';"
    res = sql_validator.validate(sql)
    assert res.is_valid is True
    assert res.status == ValidationStatus.VALID
    assert "customers" in res.parsed_tables

def test_mutating_statements_rejected(sql_validator):
    bad_queries = [
        "DELETE FROM customers WHERE id = 1;",
        "DROP TABLE orders;",
        "UPDATE products SET price = 0;",
        "INSERT INTO payments (amount) VALUES (100);",
        "ALTER TABLE customers ADD COLUMN secret TEXT;",
    ]
    for q in bad_queries:
        res = sql_validator.validate(q)
        assert res.is_valid is False
        assert res.status == ValidationStatus.DISALLOWED_OPERATION

def test_multiple_statements_rejected(sql_validator):
    sql = "SELECT * FROM orders; DROP TABLE orders;"
    res = sql_validator.validate(sql)
    assert res.is_valid is False
    assert res.status == ValidationStatus.DISALLOWED_OPERATION

def test_nonexistent_table_rejected(sql_validator):
    sql = "SELECT * FROM credit_cards_secret;"
    res = sql_validator.validate(sql)
    assert res.is_valid is False
    assert res.status == ValidationStatus.NONEXISTENT_IDENTIFIER
