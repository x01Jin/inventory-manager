"""
Database connection and management for the inventory application.
Handles SQLite database creation, connection, and basic operations.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Any, List, Dict, Union

from inventory_app.utils.logger import logger


class DatabaseConnection:
    """
    Manages SQLite database connection and operations.
    Uses composition pattern for database management.
    """

    def __init__(self, db_path: str = "inventory.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None

    class _ConnectionContext:
        """
        Context manager for database connections.
        Handles connection lifecycle and transaction rollback on errors.
        """

        def __init__(self, db_path: Path):
            self.db_path = db_path
            self.conn: Optional[sqlite3.Connection] = None

        def __enter__(self) -> sqlite3.Connection:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            return self.conn

        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            if self.conn:
                if exc_type:
                    self.conn.rollback()
                    logger.error(f"Database connection error: {exc_val}")
                self.conn.close()

    def create_database(self) -> bool:
        """
        Create database and tables if they don't exist.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            schema_path = Path(__file__).parent / "schema.sql"
            if not schema_path.exists():
                logger.error(f"Schema file not found: {schema_path}")
                return False

            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            with self.get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()

            logger.info("Database created successfully with all tables and views")
            return True

        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            return False

    def get_connection(self):
        """
        Context manager for database connections.
        Automatically handles connection opening/closing and transactions.
        """
        return self._ConnectionContext(self.db_path)

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of dictionaries representing rows
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                # Convert sqlite3.Row objects to dictionaries
                results = []
                for row in rows:
                    results.append(dict(row))

                return results

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise

    def execute_update(
        self, query: str, params: tuple = (), return_last_id: bool = False
    ) -> Union[int, tuple[int, Optional[int]]]:
        """
        Execute an INSERT, UPDATE, or DELETE query.

        Args:
            query: SQL query string
            params: Query parameters
            return_last_id: If True, also return the last insert rowid

        Returns:
            Number of affected rows, or (affected_rows, last_insert_id) if return_last_id is True
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                conn.commit()
                affected_rows = cursor.rowcount

                if return_last_id:
                    # Use the cursor's lastrowid which is the reliable last row id for
                    # the connection that executed the INSERT. Avoid querying
                    # last_insert_rowid() on a separate connection which is unreliable.
                    last_insert_id = cursor.lastrowid
                    return affected_rows, last_insert_id
                else:
                    return affected_rows

        except Exception as e:
            logger.error(f"Update execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise

    def execute_script(self, script: str) -> None:
        """
        Execute a script containing multiple SQL statements.

        Args:
            script: Multi-statement SQL script
        """
        try:
            with self.get_connection() as conn:
                conn.executescript(script)
                conn.commit()

        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            raise

    def get_last_insert_id(self) -> Optional[int]:
        """
        Get the last inserted row ID.

        Returns:
            Last insert ID or None if no connection
        """
        try:
            # This method is inherently unreliable because it opens a new
            # connection and calls SQLite's last_insert_rowid() which only
            # reports the last insert for that connection. Prefer using
            # `execute_update(..., return_last_id=True)` which returns the
            # `cursor.lastrowid` from the same connection used to perform the
            # INSERT.
            logger.warning(
                "get_last_insert_id() is deprecated and unreliable; use execute_update(..., return_last_id=True) instead"
            )
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT last_insert_rowid()")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get last insert ID: {e}")
            return None

    def database_exists(self) -> bool:
        """
        Check if database file exists and has tables.

        Returns:
            True if database exists and has tables, False otherwise
        """
        if not self.db_path.exists():
            return False

        try:
            tables = self.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            return len(tables) > 0
        except Exception:
            return False


# Global database instance
db = DatabaseConnection()
