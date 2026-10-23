import time
import sqlite3
from typing import Optional, List, Dict, Any
from app.database.connection import DatabaseConnectionManager
from app.schemas.sql import ExecutionResult
from app.config import settings

class SafeSQLExecutor:
    """
    Module H: Safe SQL Execution Engine.
    Executes validated SQL queries against SQLite in read-only mode,
    enforcing execution timeouts and row limits.
    """
    def __init__(self, connection_manager: DatabaseConnectionManager):
        self.conn_mgr = connection_manager

    def execute(
        self,
        sql: str,
        max_rows: Optional[int] = None,
        timeout_seconds: Optional[float] = None
    ) -> ExecutionResult:
        row_limit = max_rows or settings.MAX_EXECUTION_ROWS
        timeout = timeout_seconds or settings.MAX_EXECUTION_TIMEOUT_SECONDS

        start_time = time.perf_counter()
        try:
            with self.conn_mgr.get_readonly_connection() as conn:
                # Set busy timeout on connection
                conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)};")
                cursor = conn.cursor()

                # Execute statement
                cursor.execute(sql)

                # Extract column headers
                columns = [desc[0] for desc in cursor.description] if cursor.description else []

                # Fetch up to row_limit rows
                raw_rows = cursor.fetchmany(row_limit)
                rows = [list(r) for r in raw_rows]

                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return ExecutionResult(
                    success=True,
                    row_count=len(rows),
                    columns=columns,
                    rows=rows,
                    error_message=None,
                    execution_time_ms=round(elapsed_ms, 2)
                )
        except sqlite3.OperationalError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                success=False,
                row_count=0,
                columns=[],
                rows=[],
                error_message=f"Database operational error: {str(e)}",
                execution_time_ms=round(elapsed_ms, 2)
            )
        except sqlite3.DatabaseError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                success=False,
                row_count=0,
                columns=[],
                rows=[],
                error_message=f"Database execution error: {str(e)}",
                execution_time_ms=round(elapsed_ms, 2)
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                success=False,
                row_count=0,
                columns=[],
                rows=[],
                error_message=f"Unexpected execution error: {str(e)}",
                execution_time_ms=round(elapsed_ms, 2)
            )
