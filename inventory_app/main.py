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
from inventory_app.business_logic.alert_engine import alert_engine  # noqa: E402
from inventory_app.business_logic.report_generator import report_generator  # noqa: E402


def initialize_laboratory_database():
    """Initialize database with laboratory schema and seed data."""
    try:
        logger.info("🏥 Initializing Laboratory Inventory Database...")

        if not db.database_exists():
            logger.info("Creating new laboratory database...")
            if db.create_database():
                logger.info("✅ Database schema created successfully")
                seed_laboratory_data()
                logger.info("✅ Laboratory data seeded successfully")
            else:
                logger.error("❌ Failed to create database")
                return False
        else:
            logger.info("✅ Existing laboratory database found")

        return True

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


def seed_laboratory_data():
    """Seed database with initial laboratory data."""
    try:
        logger.info("Seeding laboratory inventory data...")

        # Category types are already seeded in schema.sql
        # Lifecycle rules are already seeded in schema.sql
        # Users can now add their own categories through the settings interface

        logger.info("Laboratory data seeding complete - using schema defaults")

    except Exception as e:
        logger.error(f"Failed to seed laboratory data: {e}")


def verify_components():
    """Verify that all critical components are available."""
    components_ok = True

    if not alert_engine:
        logger.warning("⚠️ Alert engine not available")
        components_ok = False

    if not report_generator:
        logger.warning("⚠️ Report generator not available")
        components_ok = False

    if components_ok:
        logger.info("✅ All components verified and ready")
    else:
        logger.warning("⚠️ Some components may not be fully functional")

    return components_ok


def main():
    """Main application entry point."""
    try:
        # Application header
        print("\n" + "="*60)
        print("🏥 LABORATORY INVENTORY MONITORING SYSTEM")
        print("="*60)
        print("Features: Equipment tracking, usage monitoring, alerts, Excel reports")
        print("Based on laboratory inventory specifications")
        print("="*60 + "\n")

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
            print("❌ GUI components not available. Please ensure PyQt6 is installed.")
            return 1

    except KeyboardInterrupt:
        logger.info("👋 Application interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"💥 Application failed: {e}")
        print(f"💥 Application error: {e}")
        return 1
    finally:
        logger.info("🏁 Laboratory inventory system shutdown complete")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
