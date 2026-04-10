"""
Entry point for the Laboratory Inventory Monitoring application.

This module initializes essential components (database, services) and
starts the GUI. It keeps startup logic minimal and provides a single
`main()` function suitable for use in process managers or when running
the package directly via `python -m inventory_app.main`.
"""

from __future__ import annotations

import os
import sys
import atexit

# Prefer package-relative imports — this will work when the module is executed
# as a package with `python -m inventory_app.main`. If the module is executed
# directly, fall back to adjusting `sys.path` so imports still resolve in dev
# environments.
try:
    from .database.connection import db
    from .utils.logger import logger
    from .services.alert_engine import alert_engine
    from .services.summary_tables import summary_tables_service
except Exception:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from inventory_app.database.connection import db
    from inventory_app.utils.logger import logger
    from inventory_app.services.alert_engine import alert_engine
    from inventory_app.services.summary_tables import summary_tables_service


def initialize_laboratory_database() -> bool:
    """Ensure the database is available and has the correct schema.

    Returns:
        bool: True if initialization was successful or if the database
        already existed; False on failure.
    """
    logger.info("Initializing Laboratory Inventory database")
    try:
        if not db.database_exists():
            logger.info("No existing database detected; creating a new one")
            if db.create_database():
                logger.info("Database initialized successfully")
            else:
                logger.error("Database creation returned failure state")
                return False
        else:
            logger.info("Existing database detected; running lightweight schema checks")

        if not ensure_development_schema_compatibility():
            logger.error("Schema compatibility checks failed")
            return False
        return True
    except Exception:
        logger.exception("Failed to initialize Laboratory Inventory database")
        return False


def ensure_development_schema_compatibility() -> bool:
    """Apply lightweight compatibility updates for development databases.

    This avoids migration churn during active development while keeping older
    local databases usable when new non-breaking columns are introduced.
    """
    try:
        columns = db.execute_query("PRAGMA table_info(Items)")
        item_columns = {row.get("name") for row in columns}

        if "item_type" not in item_columns:
            logger.info("Adding missing Items.item_type column for compatibility")
            db.execute_update("ALTER TABLE Items ADD COLUMN item_type TEXT")
            db.execute_update(
                """
                UPDATE Items
                SET item_type = CASE
                    WHEN is_consumable = 1 THEN 'Consumable'
                    ELSE 'Non-consumable'
                END
                WHERE item_type IS NULL OR TRIM(item_type) = ''
                """
            )

        return True
    except Exception:
        logger.exception("Failed to apply development schema compatibility updates")
        return False


def run_migrations_with_splash(app) -> bool:
    """Run pending migrations with splash screen.

    Args:
        app: QApplication instance needed for splash screen

    Returns:
        bool: True if all migrations succeeded, False on failure
    """
    from inventory_app.database.migrations import migration_manager
    from inventory_app.gui.splash_screen import SplashScreen

    pending = migration_manager.get_pending_migrations()
    if not pending:
        return True

    splash = SplashScreen()
    splash.show()
    app.processEvents()

    try:
        migration_manager.run_pending_migrations(
            progress_callback=lambda status, percent: (
                splash.update_progress(status, percent),
                app.processEvents(),
                None,
            )[-1]
        )
        splash.close()
        return True
    except Exception:
        logger.exception("Migration failed")
        splash.close()
        return False


def verify_components() -> bool:
    """Quick sanity checks for critical services used by the application.

    At the moment the only check performed is to confirm the alert engine
    exists. This function returns ``True`` if all checks pass; otherwise
    ``False``.
    """
    if alert_engine is None:
        logger.warning("Alert engine not available; some features will be degraded")
        return False
    logger.info("All critical components are available")
    return True


def main() -> int:
    """Start the application and return a suitable process exit code.

    Return codes:
        0: Clean exit (user interruption or GUI returned success)
        1: Startup failure (database, imports, or unexpected error)
    """
    logger.info("Laboratory Inventory Monitoring System: starting up")
    try:
        if not initialize_laboratory_database():
            logger.error("Application startup failed: database initialization error")
            return 1

        # Import GUI components and create application early for splash screen
        try:
            from PyQt6.QtWidgets import QApplication
            from inventory_app.gui.main_window import main as gui_main
        except ImportError:
            logger.exception(
                "Failed to import GUI components. Confirm PyQt6 and GUI packages are installed."
            )
            return 1

        app = QApplication(sys.argv)

        # Run migrations with splash if needed
        if not run_migrations_with_splash(app):
            logger.error("Application startup failed: migration error")
            return 1

        if not verify_components():
            logger.warning(
                "One or more components failed verification; continuing startup"
            )

        # Initialize summary tables service (Chunk 8)
        try:
            if summary_tables_service.initialize():
                logger.info("Summary tables service initialized")
                # Backfill summaries if this is a new database
                summary_tables_service.backfill_summaries()
                atexit.register(summary_tables_service.shutdown)
            else:
                logger.warning(
                    "Summary tables service initialization failed; continuing without summary tables"
                )
        except Exception as e:
            logger.warning(
                f"Summary tables service unavailable: {e}; continuing without summary tables"
            )

        logger.info("Launching GUI")
        gui_exit_code = gui_main()
        if isinstance(gui_exit_code, int):
            return gui_exit_code
        return 0
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user (KeyboardInterrupt)")
        return 0
    except Exception:
        logger.exception("Unexpected error during application startup")
        return 1
    finally:
        logger.info("Laboratory inventory system shutdown complete")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
