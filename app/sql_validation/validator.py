import re
from typing import List, Set, Optional, Tuple
import sqlglot
from sqlglot import exp
from app.schemas.sql import ValidationResult, ValidationStatus

class SQLValidator:
    """
    Module H: AST-based SQL Validation Security Boundary.
    Enforces strict read-only execution:
    - Parses SQL with sqlglot
    - Permits ONLY single-statement SELECT or read-only CTE queries
    - Blocks INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH, PRAGMA, EXEC, etc.
    - Validates referenced table names against allowed database schema
    - Rejects multiple semicolon-delimited queries
    """
    def __init__(self, allowed_tables: Optional[List[str]] = None):
        self.allowed_tables = set(t.lower() for t in (allowed_tables or []))

    def update_allowed_tables(self, tables: List[str]):
        self.allowed_tables = set(t.lower() for t in tables)

    def validate(self, sql_query: str) -> ValidationResult:
        raw_sql = sql_query.strip()
        if not raw_sql:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.SYNTAX_ERROR,
                error_message="SQL query cannot be empty."
            )

        # Remove trailing semicolons and check for multiple statements
        cleaned_sql = raw_sql.rstrip(";")
        if ";" in cleaned_sql:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.DISALLOWED_OPERATION,
                error_message="Multiple statements detected. Semicolon-delimited queries are forbidden."
            )

        # Parse AST with sqlglot (sqlite dialect)
        try:
            parsed_statements = sqlglot.parse(cleaned_sql, read="sqlite")
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.SYNTAX_ERROR,
                error_message=f"SQL syntax parse error: {str(e)}"
            )

        if not parsed_statements:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.SYNTAX_ERROR,
                error_message="No valid SQL statement parsed."
            )

        if len(parsed_statements) > 1:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.DISALLOWED_OPERATION,
                error_message="Multiple SQL statements are not permitted."
            )

        statement = parsed_statements[0]
        if statement is None:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.SYNTAX_ERROR,
                error_message="Null AST parsed."
            )

        # Ensure root statement is SELECT or read-only CTE
        if not isinstance(statement, (exp.Select, exp.Union)):
            # If it's a CTE, root is still Select or Union
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.DISALLOWED_OPERATION,
                error_message=f"Statement of type {type(statement).__name__} is disallowed. Only SELECT queries are permitted."
            )

        # Inspect AST nodes for forbidden expressions
        prohibited_expressions = (
            exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
            exp.Alter, exp.Pragma, exp.Command, exp.Transaction
        )
        for node in statement.walk():
            if isinstance(node, prohibited_expressions):
                return ValidationResult(
                    is_valid=False,
                    status=ValidationStatus.DISALLOWED_OPERATION,
                    error_message=f"Disallowed mutating operation: {type(node).__name__}"
                )

        # Extract table references
        referenced_tables = []
        for table_expr in statement.find_all(exp.Table):
            tbl_name = table_expr.name.lower()
            if tbl_name and tbl_name not in referenced_tables:
                referenced_tables.append(tbl_name)

        # Validate against allowed tables if configured
        if self.allowed_tables:
            for tbl in referenced_tables:
                # Exclude CTE aliases defined in WITH clause
                cte_names = [cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)]
                if tbl not in self.allowed_tables and tbl not in cte_names:
                    return ValidationResult(
                        is_valid=False,
                        status=ValidationStatus.NONEXISTENT_IDENTIFIER,
                        error_message=f"Referenced table '{tbl}' does not exist in schema.",
                        parsed_tables=referenced_tables
                    )

        # Extract column references
        referenced_columns = []
        for col_expr in statement.find_all(exp.Column):
            col_name = col_expr.name
            if col_name and col_name not in referenced_columns:
                referenced_columns.append(col_name)

        return ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            error_message=None,
            parsed_tables=referenced_tables,
            parsed_columns=referenced_columns
        )
