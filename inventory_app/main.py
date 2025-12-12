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

# Prefer package-relative imports — this will work when the module is executed
# as a package with `python -m inventory_app.main`. If the module is executed
# directly, fall back to adjusting `sys.path` so imports still resolve in dev
# environments.
try:
    from .database.connection import db
    from .utils.logger import logger
    from .services.alert_engine import alert_engine
except Exception:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from inventory_app.database.connection import db
    from inventory_app.utils.logger import logger
    from inventory_app.services.alert_engine import alert_engine


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
            logger.info("Existing database detected; schema verification skipped")
        return True
    except Exception:
        logger.exception("Failed to initialize Laboratory Inventory database")
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

        if not verify_components():
            logger.warning(
                "One or more components failed verification; continuing startup"
            )

        # Import GUI components only after database initialization succeeds
        try:
            from inventory_app.gui.main_window import main as gui_main  # Local import
        except ImportError:
            logger.exception(
                "Failed to import GUI components. Confirm PyQt6 and GUI packages are installed."
            )
            return 1

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
