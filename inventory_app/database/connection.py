"""
Database connection and management for the inventory application.
Handles SQLite database creation, connection, and basic operations.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Any, List, Dict, Union, overload, Tuple, Literal

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
        # If a transaction is active, this holds the sqlite3.Connection
        self._transaction_conn: Optional[sqlite3.Connection] = None

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

    class _TransactionContext:
        """
        Context manager for atomic multi-statement transactions.
        When active, `execute_query`, `execute_update` and `execute_script`
        will use the same connection for all statements so they can be
        committed or rolled back together.
        """

        def __init__(self, parent: "DatabaseConnection", immediate: bool = False):
            self.parent = parent
            self.conn: Optional[sqlite3.Connection] = None
            self.immediate = immediate

        def __enter__(self) -> sqlite3.Connection:
            if self.parent._transaction_conn is not None:
                raise RuntimeError("Nested transactions are not supported")
            self.conn = sqlite3.connect(self.parent.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.row_factory = sqlite3.Row
            # If the caller requested an immediate transaction, begin one
            # with `BEGIN IMMEDIATE` to obtain a write lock early and prevent
            # concurrent writers from making conflicting changes.
            if self.immediate:
                self.conn.execute("BEGIN IMMEDIATE")
            self.parent._transaction_conn = self.conn
            return self.conn

        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            if self.conn:
                if exc_type:
                    self.conn.rollback()
                    logger.error(f"Transaction error: {exc_val}")
                else:
                    self.conn.commit()
                self.conn.close()
                self.parent._transaction_conn = None

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

    def transaction(self, immediate: bool = False):
        """
        Transactional context manager that allows executing multiple
        statements atomically. Example:

            with db.transaction():
                db.execute_update(...)
                db.execute_update(...)

        All `execute_update` calls inside the context will run on the
        same connection and will be committed/rolled back together.
        """
        return self._TransactionContext(self, immediate=immediate)

    def in_transaction(self) -> bool:
        """
        Return True if a transaction context is currently active on this
        DatabaseConnection instance.
        """
        return self._transaction_conn is not None

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
            if self._transaction_conn is not None:
                conn = self._transaction_conn
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
            else:
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

    @overload
    def execute_update(
        self, query: str, params: tuple = (), *, return_last_id: Literal[True]
    ) -> Tuple[int, Optional[int]]: ...

    @overload
    def execute_update(
        self, query: str, params: tuple = (), *, return_last_id: Literal[False] = False
    ) -> int: ...

    def execute_update(
        self, query: str, params: tuple = (), return_last_id: bool = False
    ) -> Union[int, Tuple[int, Optional[int]]]:
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
            # Use the active transaction connection if available; do not commit
            # while inside a transaction because the transaction manager will
            # handle commit/rollback at the end of the context.
            if self._transaction_conn is not None:
                conn = self._transaction_conn
                cursor = conn.execute(query, params)
                affected_rows = cursor.rowcount
                if return_last_id:
                    last_insert_id = cursor.lastrowid
                    return affected_rows, last_insert_id
                return affected_rows
            else:
                with self.get_connection() as conn:
                    cursor = conn.execute(query, params)
                    conn.commit()
                    affected_rows = cursor.rowcount
                    if return_last_id:
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
            if self._transaction_conn is not None:
                conn = self._transaction_conn
                conn.executescript(script)
            else:
                with self.get_connection() as conn:
                    conn.executescript(script)
                    conn.commit()

        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            raise

    # Removed `get_last_insert_id()` in favor of `execute_update(..., return_last_id=True)`
    # which returns the `cursor.lastrowid` from the connection used for the INSERT.

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
