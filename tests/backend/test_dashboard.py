import pytest
from datetime import datetime, timedelta, timezone, date
from inventory_app.database.connection import db
from inventory_app.utils.activity_logger import ActivityLogger
from inventory_app.gui.dashboard.metrics import MetricsManager
from inventory_app.gui.dashboard.metrics_worker import get_consolidated_metrics
from inventory_app.gui.reports.data_sources import (
    get_expiration_data,
    get_calibration_due_data,
)
from inventory_app.services.alert_engine import alert_engine


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test and ensure schema is applied."""
    db_file = tmp_path / "test_inventory.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file


def test_activity_logger_retention(temp_db):
    """Verify behavior: unlimited retention with no automatic pruning."""
    # Insert one old record (100 days old) and one recent record (10 days old)
    old_ts = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    recent_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

    insert_q = """
    INSERT INTO Activity_Log (activity_type, description, entity_id, entity_type, user_name, timestamp)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    db.execute_update(
        insert_q, ("ITEM_ADDED", "Old activity", None, None, "tester", old_ts)
    )
    db.execute_update(
        insert_q, ("ITEM_ADDED", "Recent activity", None, None, "tester", recent_ts)
    )

    # Default cleanup call should perform no deletion.
    ActivityLogger.cleanup_old_activities()

    remaining = db.execute_query("SELECT COUNT(*) as count FROM Activity_Log")[0][
        "count"
    ]
    assert remaining == 2

    # Verify limit cleanup
    for i in range(50):
        db.execute_update(
            insert_q, ("ITEM_ADDED", f"Activity {i}", None, None, "tester", recent_ts)
        )

    # Default limit maintenance should perform no deletion.
    ActivityLogger.maintain_activity_limit()
    remaining = db.execute_query("SELECT COUNT(*) as count FROM Activity_Log")[0][
        "count"
    ]
    assert remaining == 52


def test_metrics_query_integrity(temp_db):
    """Ensure dashboard metrics are calculated correctly and use parameterization."""
    mgr = MetricsManager()

    # Populate some data
    db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)", ("Item 1", 1)
    )
    db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)", ("Item 2", 1)
    )

    metrics = mgr.get_all_metrics()
    assert metrics["total_items"] == 2

    # Test low stock metric specifically
    # Create an item with low stock (current < 10 AND > 0)
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("Low Item", 1),
        return_last_id=True,
    )[1]
    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 10, "2025-01-01"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?)",
        (item_id, "CONSUMPTION", 5, "2025-01-01"),
    )

    metrics = mgr.get_all_metrics()
    assert metrics["low_stock"] >= 1


def test_alert_data_retrieval(temp_db):
    """Verify that expiration and calibration alert data can be retrieved."""
    today = date.today()
    start_date = today
    end_date = today + timedelta(days=180)

    # Insert an expiring item (30 days from now is within the test's 180 day window)
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, expiration_date) VALUES (?, ?, ?)",
        ("Expiring Item", 1, (today + timedelta(days=30)).isoformat()),
        return_last_id=True,
    )[1]
    # Must have stock to show in alerts
    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 1, "2025-01-01"),
    )

    # Expiration alerts
    exp_data = get_expiration_data(start_date, end_date)
    assert any(str(d.get("Item Name", "")).lower() == "expiring item" for d in exp_data)

    # Insert an item needing calibration
    equipment_id = db.execute_query(
        "SELECT id FROM Categories WHERE name = ?", ("Equipment",)
    )[0]["id"]
    cal_id = db.execute_update(
        "INSERT INTO Items (name, category_id, calibration_date) VALUES (?, ?, ?)",
        ("Calib Item", equipment_id, (today + timedelta(days=30)).isoformat()),
        return_last_id=True,
    )[1]
    # Must have stock to show in alerts
    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (cal_id, 1, 1, "2025-01-01"),
    )

    # Calibration alerts
    cal_data = get_calibration_due_data(start_date, end_date)
    assert any(str(d.get("Item Name", "")).lower() == "calib item" for d in cal_data)


def test_activity_log_triggers(temp_db):
    """Verify no schema triggers automatically prune Task 9 activity logs."""
    insert_q = """
    INSERT INTO Activity_Log (activity_type, description, entity_id, entity_type, user_name, timestamp)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    # Exceed old threshold; records must all remain.
    for i in range(25):
        db.execute_update(
            insert_q,
            (
                "ITEM_EDITED",
                f"Activity {i}",
                None,
                None,
                "tester",
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    total = db.execute_query("SELECT COUNT(*) as count FROM Activity_Log")[0]["count"]
    assert total == 25


def test_dashboard_expiring_metric_uses_status_windows(temp_db):
    """Expiring metric should follow item status windows, not a fixed 30-day SQL cutoff."""
    today = date.today()

    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, expiration_date) VALUES (?, ?, ?)",
        ("120-Day Consumable", 1, (today + timedelta(days=120)).isoformat()),
        return_last_id=True,
    )[1]
    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 5, today.isoformat()),
    )

    consolidated = get_consolidated_metrics()
    manager_metrics = MetricsManager().get_all_metrics()

    assert consolidated["expiring_soon"] >= 1
    assert manager_metrics["expiring_soon"] >= 1


def test_calibration_report_filters_to_calibration_categories(temp_db):
    """Calibration due report should include only categories configured for calibration."""
    today = date.today()

    categories = db.execute_query("SELECT id, name FROM Categories")
    cat_ids = {row["name"]: row["id"] for row in categories}

    equipment_id = db.execute_update(
        "INSERT INTO Items (name, category_id, calibration_date) VALUES (?, ?, ?)",
        (
            "Equipment Cal Item",
            cat_ids["Equipment"],
            (today + timedelta(days=30)).isoformat(),
        ),
        return_last_id=True,
    )[1]
    apparatus_id = db.execute_update(
        "INSERT INTO Items (name, category_id, calibration_date) VALUES (?, ?, ?)",
        (
            "Apparatus Cal Item",
            cat_ids["Apparatus"],
            (today + timedelta(days=30)).isoformat(),
        ),
        return_last_id=True,
    )[1]

    for item_id in (equipment_id, apparatus_id):
        db.execute_update(
            "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
            (item_id, 1, 1, today.isoformat()),
        )

    rows = get_calibration_due_data(today, today + timedelta(days=180))
    item_names = {str(r.get("Item Name", "")).lower() for r in rows}

    assert "equipment cal item" in item_names
    assert "apparatus cal item" not in item_names


def test_disposal_alert_labels_for_non_consumables(temp_db):
    """Non-consumables should surface disposal-specific alert labels."""
    today = date.today()

    categories = db.execute_query("SELECT id, name FROM Categories")
    cat_ids = {row["name"]: row["id"] for row in categories}

    warning_item = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable, expiration_date) VALUES (?, ?, ?, ?)",
        (
            "Apparatus Warning",
            cat_ids["Apparatus"],
            0,
            (today + timedelta(days=30)).isoformat(),
        ),
        return_last_id=True,
    )[1]
    overdue_item = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable, expiration_date) VALUES (?, ?, ?, ?)",
        (
            "Apparatus Overdue",
            cat_ids["Apparatus"],
            0,
            (today - timedelta(days=1)).isoformat(),
        ),
        return_last_id=True,
    )[1]

    for item_id in (warning_item, overdue_item):
        db.execute_update(
            "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
            (item_id, 1, 1, today.isoformat()),
        )

    alerts = alert_engine.get_all_alerts()
    alerts_by_name = {a.item_name: a.alert_type for a in alerts}
    warning_alert = next(
        (a for a in alerts if a.item_name == "Apparatus Warning"), None
    )

    assert alerts_by_name.get("Apparatus Warning") == "disposal warning"
    assert alerts_by_name.get("Apparatus Overdue") == "disposal overdue"
    assert warning_alert is not None
    assert warning_alert.batch_label == "B1"
