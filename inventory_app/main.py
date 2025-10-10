"""
Main entry point for the Laboratory Inventory Monitoring Application.
Brings together all components: database, business logic, and GUI.
"""

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from inventory_app.database.connection import db  # noqa: E402
from inventory_app.utils.logger import logger  # noqa: E402
from inventory_app.services.alert_engine import alert_engine  # noqa: E402

def initialize_laboratory_database():
    """Initialize database with laboratory schema and seed data."""
    try:
        logger.info("🏥 Initializing Laboratory Inventory Database...")

        if not db.database_exists():
            logger.info("Creating new laboratory database...")
            if db.create_database():
                logger.info("✅ Database schema created successfully")
            else:
                logger.error("❌ Failed to create database")
                return False
        else:
            logger.info("✅ Existing laboratory database found")

        return True

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

def verify_components():
    """Verify that all critical components are available."""
    components_ok = True

    if not alert_engine:
        logger.warning("⚠️ Alert engine not available")
        components_ok = False

    if components_ok:
        logger.info("✅ All components verified and ready")
    else:
        logger.warning("⚠️ Some components may not be fully functional")

    return components_ok

def main():
    """Main application entry point."""
    try:
        logger.info("🏥 LABORATORY INVENTORY MONITORING SYSTEM")
        logger.info("Starting Laboratory Inventory Application...")

        # Initialize database
        if not initialize_laboratory_database():
            logger.error("❌ Application startup failed - database initialization error")
            return 1

        # Verify components
        verify_components()

        # Import and start GUI (only after database is ready)
        try:
            from inventory_app.gui.main_window import main as gui_main
            logger.info("✅ Starting laboratory inventory GUI...")
            return gui_main()
        except ImportError as e:
            logger.error(f"❌ GUI import failed: {e}")
            logger.error("❌ GUI components not available. Please ensure PyQt6 is installed.")
            return 1

    except KeyboardInterrupt:
        logger.info("👋 Application interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"💥 Application failed: {e}")
        logger.error(f"💥 Application error: {e}")
        return 1
    finally:
        logger.info("🏁 Laboratory inventory system shutdown complete")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
