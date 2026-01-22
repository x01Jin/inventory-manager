import pytest
from datetime import datetime, timedelta, timezone, date
from inventory_app.database.connection import db
from inventory_app.utils.activity_logger import ActivityLogger
from inventory_app.gui.dashboard.metrics import MetricsManager
from inventory_app.gui.reports.data_sources import (
    get_expiration_data,
    get_calibration_due_data,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test and ensure schema is applied."""
    db_file = tmp_path / "test_inventory.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file


def test_activity_logger_retention(temp_db):
    """Verify that old activities are cleaned up according to retention policy."""
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

    # Trigger cleanup
    ActivityLogger.cleanup_old_activities(days_to_keep=90)

    remaining = db.execute_query("SELECT COUNT(*) as count FROM Activity_Log")[0][
        "count"
    ]
    assert remaining == 1

    # Verify limit cleanup
    for i in range(50):
        db.execute_update(
            insert_q, ("ITEM_ADDED", f"Activity {i}", None, None, "tester", recent_ts)
        )

    # Trigger limit cleanup (usually capped at 20 in triggers, but let's test the utility)
    ActivityLogger.maintain_activity_limit(max_activities=20)
    remaining = db.execute_query("SELECT COUNT(*) as count FROM Activity_Log")[0][
        "count"
    ]
    assert remaining <= 20


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
    cal_id = db.execute_update(
        "INSERT INTO Items (name, category_id, calibration_date) VALUES (?, ?, ?)",
        ("Calib Item", 1, (today + timedelta(days=30)).isoformat()),
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
    """Verify database triggers automatically handle activity log maintenance."""
    insert_q = """
    INSERT INTO Activity_Log (activity_type, description, entity_id, entity_type, user_name, timestamp)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    # Exceed limit to trigger automatic pruning
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
    # Trigger from schema.sql should keep it at 20
    assert total <= 20
