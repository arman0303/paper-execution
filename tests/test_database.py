import pytest
import sqlite3

def test_readonly_connection_blocks_mutations(conn_manager):
    with conn_manager.get_readonly_connection() as conn:
        cursor = conn.cursor()
        with pytest.raises(sqlite3.OperationalError):
            cursor.execute("INSERT INTO customers (name, email, city, country) VALUES ('Hacker', 'h@x.com', 'X', 'Y');")

def test_schema_introspector_finds_tables(introspector):
    tables = introspector.get_table_names()
    assert "customers" in tables
    assert "orders" in tables
    assert "order_items" in tables
    assert "products" in tables
    assert "payments" in tables

def test_foreign_keys_correctly_detected(introspector):
    orders_info = introspector.inspect_table_schema("orders")
    fks = orders_info["foreign_keys"]
    customer_fks = [fk for fk in fks if fk["to_table"] == "customers" and fk["from_column"] == "customer_id"]
    assert len(customer_fks) == 1
    assert "customers" in orders_info["connected_tables"]
