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
from inventory_app.database.models import CategoryType, Category, Lifecycle_Rules  # noqa: E402
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
    """Seed database with initial laboratory categories and suppliers."""
    try:
        logger.info("Seeding laboratory inventory data...")

        # Check if category types already exist (from schema.sql)
        existing_types = CategoryType.get_all()
        existing_type_names = [ct.name for ct in existing_types]

        created_types = {}
        for ct in existing_types:
            created_types[ct.name] = ct.id

        # Create category types only if they don't exist
        category_types = ["Chemical", "Glassware", "Equipment", "Apparatus", "Material"]

        for name in category_types:
            if name not in existing_type_names:
                cat_type = CategoryType(name=name)
                if cat_type.save():
                    created_types[name] = cat_type.id
                    logger.debug(f"Created category type: {name}")
                else:
                    logger.error(f"Failed to create category type: {name}")
            else:
                logger.debug(f"Category type already exists: {name}")

        # Create lifecycle rules (check if they already exist from schema.sql)
        lifecycle_data = [
            (created_types["Chemical"], 6, None, None, None),  # 6 months expiration
            (created_types["Glassware"], None, 3, None, None), # 3 years lifespan
            (created_types["Equipment"], None, 5, 12, 3),      # 5 years + yearly calibration
            (created_types["Apparatus"], None, 5, None, None),  # 5 years lifespan
            (created_types["Material"], None, 2, None, None)    # 2 years lifespan
        ]

        for type_id, exp, life, cal_int, cal_lead in lifecycle_data:
            if type_id:
                # Check if rule already exists for this category type
                existing_rule = Lifecycle_Rules.get_by_category_type(type_id)
                if existing_rule:
                    logger.debug(f"Lifecycle rule already exists for category type {type_id}")
                else:
                    rule = Lifecycle_Rules(
                        category_type_id=type_id,
                        expiry_lead_months=exp,
                        lifespan_years=life,
                        calibration_interval_months=cal_int,
                        calibration_lead_months=cal_lead
                    )
                    if rule.save():
                        logger.debug(f"Created lifecycle rule for category type {type_id}")
                    else:
                        logger.error(f"Failed to create lifecycle rule for category type {type_id}")

        # Create default categories (check if they already exist)
        categories = [
            ("Chemicals", created_types["Chemical"]),
            ("Beakers", created_types["Glassware"]),
            ("Flasks", created_types["Glassware"]),
            ("Microscopes", created_types["Equipment"]),
            ("Pipettes", created_types["Apparatus"])
        ]

        existing_categories = Category.get_all()
        existing_names = [c.name for c in existing_categories]

        for name, type_id in categories:
            if type_id and name not in existing_names:
                category = Category(name=name, category_type_id=type_id)
                if category.save():
                    logger.debug(f"Created category: {name}")
                else:
                    logger.error(f"Failed to create category: {name}")
            elif name in existing_names:
                logger.debug(f"Category already exists: {name}")

        logger.info("Laboratory data seeding complete")

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
