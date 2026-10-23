import sqlite3
from pathlib import Path
from typing import Generator
from contextlib import contextmanager

class DatabaseConnectionManager:
    def __init__(self, db_path: str):
        self.db_path = str(Path(db_path).resolve())

    @contextmanager
    def get_readonly_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Provides a strictly read-only SQLite connection using URI mode=ro and query_only=ON.
        """
        # On Windows, sqlite URI paths need forward slashes
        norm_path = self.db_path.replace("\\", "/")
        uri = f"file:///{norm_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("PRAGMA query_only = ON;")
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def get_readwrite_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Read-write connection for test fixture setups and seeding."""
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
