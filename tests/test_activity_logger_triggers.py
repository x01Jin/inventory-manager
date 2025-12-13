from datetime import datetime, timedelta, timezone
from pathlib import Path
from inventory_app.database.connection import db


def setup_temp_db(tmp_path: Path):
    tmp_db_path = tmp_path / "test_inventory_triggers.db"
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    created = db.create_database()
    assert created is True
    return tmp_db_path


def test_trigger_maintains_limit_on_insert(tmp_path: Path):
    setup_temp_db(tmp_path)

    # Insert 25 records to exceed the trigger limit of 20
    insert_q = """
    INSERT INTO Activity_Log (activity_type, description, entity_id, entity_type, user_name, timestamp)
    VALUES (?, ?, ?, ?, ?, ?)
    """

    now = datetime.now(timezone.utc)
    for i in range(25):
        ts = (now - timedelta(minutes=(25 - i))).isoformat()
        db.execute_update(
            insert_q, ("ITEM_EDITED", f"Activity {i}", None, None, "tester", ts)
        )

    # After insertions, the trigger should have pruned to 20 rows
    total_after = db.execute_query("SELECT COUNT(*) as count FROM Activity_Log")[0][
        "count"
    ]
    assert total_after == 20


def test_trigger_deletes_old_activities_by_days(tmp_path: Path):
    setup_temp_db(tmp_path)

    # Insert one very old record (100 days ago) and then a new insert to trigger cleanup
    old_ts = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    insert_q = """
    INSERT INTO Activity_Log (activity_type, description, entity_id, entity_type, user_name, timestamp)
    VALUES (?, ?, ?, ?, ?, ?)
    """

    db.execute_update(
        insert_q, ("ITEM_ADDED", "Very old activity", None, None, "tester", old_ts)
    )
    # Insert one new record that should trigger a cleanup
    recent_ts = datetime.now(timezone.utc).isoformat()
    db.execute_update(
        insert_q, ("ITEM_ADDED", "Recent activity", None, None, "tester", recent_ts)
    )

    # After trigger runs, expect the old activity removed due to 90-day retention
    rows = db.execute_query("SELECT timestamp FROM Activity_Log")
    assert all(
        datetime.fromisoformat(r["timestamp"])
        >= (datetime.now(timezone.utc) - timedelta(days=90))
        for r in rows
    )
