"""
Database migration framework.

Migrations are numbered Python files in this directory (e.g., 001_*.py, 002_*.py).
Each migration must define:
- description: A string explaining what the migration does
- up(): A function that applies the migration
"""

from .migration_manager import MigrationManager

migration_manager = MigrationManager(__file__)

__all__ = ["migration_manager"]
