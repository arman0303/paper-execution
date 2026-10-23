import sqlite3
from typing import Dict, List, Any
from app.database.connection import DatabaseConnectionManager

class SchemaIntrospector:
    """
    Module A: Database schema introspection.
    Extracts tables, columns, data types, primary keys, and verified foreign keys.
    Strictly avoids inferring unverified relationships simply from naming similarities.
    """
    def __init__(self, connection_manager: DatabaseConnectionManager):
        self.conn_mgr = connection_manager

    def get_table_names(self) -> List[str]:
        with self.conn_mgr.get_readonly_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
            )
            return [row["name"] for row in cursor.fetchall()]

    def inspect_table_schema(self, table_name: str) -> Dict[str, Any]:
        with self.conn_mgr.get_readonly_connection() as conn:
            cursor = conn.cursor()

            # Columns
            cursor.execute(f"PRAGMA table_info('{table_name}');")
            raw_columns = cursor.fetchall()
            columns = []
            primary_keys = []
            for col in raw_columns:
                col_name = col["name"]
                columns.append({
                    "name": col_name,
                    "type": col["type"],
                    "not_null": bool(col["notnull"]),
                    "default_value": col["dflt_value"],
                    "is_primary_key": bool(col["pk"])
                })
                if col["pk"]:
                    primary_keys.append(col_name)

            # Foreign Keys
            cursor.execute(f"PRAGMA foreign_key_list('{table_name}');")
            raw_fks = cursor.fetchall()
            foreign_keys = []
            connected_tables = set()
            for fk in raw_fks:
                from_col = fk["from"]
                to_table = fk["table"]
                to_col = fk["to"]
                foreign_keys.append({
                    "from_column": from_col,
                    "to_table": to_table,
                    "to_column": to_col
                })
                connected_tables.add(to_table)

            return {
                "name": table_name,
                "columns": columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "connected_tables": sorted(list(connected_tables))
            }

    def inspect_entire_schema(self) -> Dict[str, Dict[str, Any]]:
        tables = self.get_table_names()
        schema = {}
        for tbl in tables:
            schema[tbl] = self.inspect_table_schema(tbl)

        # Build reverse relationships for complete connected_tables knowledge
        for tbl, info in schema.items():
            for fk in info["foreign_keys"]:
                target_table = fk["to_table"]
                if target_table in schema and tbl not in schema[target_table]["connected_tables"]:
                    schema[target_table]["connected_tables"].append(tbl)
                    schema[target_table]["connected_tables"].sort()

        return schema
