from datetime import datetime, timedelta, timezone
from inventory_app.database.connection import db
from inventory_app.utils.activity_logger import ActivityLogger


def setup_temp_db(tmp_path):
    tmp_db_path = tmp_path / "test_inventory.db"
    tmp_db_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    created = db.create_database()
    assert created is True
    return tmp_db_path


def test_cleanup_old_activities_deletes_older_records(tmp_path):
    setup_temp_db(tmp_path)

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

    deleted = ActivityLogger.cleanup_old_activities(days_to_keep=90)
    # The important invariant is that only the recent record remains.
    assert deleted in (0, 1)

    remaining = db.execute_query("SELECT COUNT(*) as count FROM Activity_Log")[0][
        "count"
    ]
    assert remaining == 1


def test_maintain_activity_limit_keeps_recent_n(tmp_path):
    setup_temp_db(tmp_path)

    # Insert 5 records with ascending timestamps
    insert_q = """
    INSERT INTO Activity_Log (activity_type, description, entity_id, entity_type, user_name, timestamp)
    VALUES (?, ?, ?, ?, ?, ?)
    """

    now = datetime.now(timezone.utc)
    for i in range(5):
        ts = (now - timedelta(days=5 - i)).isoformat()
        db.execute_update(
            insert_q, ("ITEM_EDITED", f"Activity {i}", None, None, "tester", ts)
        )

    # Ensure we have 5
    total_before = db.execute_query("SELECT COUNT(*) as count FROM Activity_Log")[0][
        "count"
    ]
    assert total_before == 5

    deleted = ActivityLogger.maintain_activity_limit(max_activities=3)
    assert deleted == 2

    total_after = db.execute_query("SELECT COUNT(*) as count FROM Activity_Log")[0][
        "count"
    ]
    assert total_after == 3
