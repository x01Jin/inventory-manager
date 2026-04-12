from datetime import date

import pytest

from inventory_app.database.connection import db
from scripts.sample_data import GenerationConfig, InventorySimulation


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_sample_data.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file


def test_business_day_calendar_excludes_weekends_and_ph_holidays():
    config = GenerationConfig(reset_before_generate=False)
    sim = InventorySimulation(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 12),
        config=config,
    )

    sim._build_business_day_calendar()
    business_days = set(sim._business_days)

    assert date(2026, 4, 4) not in business_days
    assert date(2026, 4, 5) not in business_days
    assert date(2026, 4, 2) not in business_days
    assert date(2026, 4, 3) not in business_days
    assert date(2026, 4, 9) not in business_days
    assert date(2026, 4, 6) in business_days


def test_reset_simulation_data_clears_operational_tables(temp_db):
    requester_id = db.execute_update(
        "INSERT INTO Requesters (name, requester_type) VALUES (?, ?)",
        ("Reset User", "teacher"),
        return_last_id=True,
    )[1]
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Reset Item", 1, 1),
        return_last_id=True,
    )[1]
    batch_id = db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, date_received, quantity_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, "2026-01-01", 100),
        return_last_id=True,
    )[1]
    requisition_id = db.execute_update(
        """
        INSERT INTO Requisitions (
            requester_id, expected_request, expected_return, status,
            lab_activity_name, lab_activity_date
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            requester_id,
            "2026-01-10 08:00:00",
            "2026-01-12 16:00:00",
            "requested",
            "Reset Activity",
            "2026-01-10",
        ),
        return_last_id=True,
    )[1]
    db.execute_update(
        "INSERT INTO Requisition_Items (requisition_id, item_id, quantity_requested) VALUES (?, ?, ?)",
        (requisition_id, item_id, 5),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date, source_id) VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, batch_id, "CONSUMPTION", 5, "2026-01-10", requisition_id),
    )

    sim = InventorySimulation(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        config=GenerationConfig(reset_before_generate=True),
    )
    sim._reset_simulation_data()

    assert db.execute_query("SELECT COUNT(*) AS c FROM Requisitions")[0]["c"] == 0
    assert db.execute_query("SELECT COUNT(*) AS c FROM Requisition_Items")[0]["c"] == 0
    assert db.execute_query("SELECT COUNT(*) AS c FROM Stock_Movements")[0]["c"] == 0
    assert db.execute_query("SELECT COUNT(*) AS c FROM Items")[0]["c"] == 0
    assert db.execute_query("SELECT COUNT(*) AS c FROM Requesters")[0]["c"] == 0
    assert db.execute_query("SELECT COUNT(*) AS c FROM Categories")[0]["c"] > 0


def test_small_generation_hits_density_and_date_invariants(temp_db):
    config = GenerationConfig(
        seed=777,
        target_requisitions=30,
        target_requisition_items=300,
        target_stock_movements=900,
        reset_before_generate=True,
        min_items_per_requisition=8,
        max_items_per_requisition=14,
    )
    sim = InventorySimulation(
        start_date=date(2026, 1, 2),
        end_date=date(2026, 4, 12),
        config=config,
    )

    stats = sim.run()

    assert stats["requisitions_created"] >= 30
    assert stats["requisition_items_created"] >= 300
    assert stats["stock_movements_created"] >= 900

    rows = db.execute_query("SELECT lab_activity_date FROM Requisitions")
    assert rows
    for row in rows:
        d = date.fromisoformat(row["lab_activity_date"])
        assert d.weekday() < 5
        assert d not in InventorySimulation.PH_NON_WORKING_HOLIDAYS

    status_rows = db.execute_query(
        "SELECT status, COUNT(*) AS c FROM Requisitions GROUP BY status"
    )
    statuses = {r["status"] for r in status_rows}
    assert "requested" in statuses
    assert "active" in statuses

    movement_rows = db.execute_query(
        "SELECT DISTINCT movement_type FROM Stock_Movements"
    )
    movement_types = {r["movement_type"] for r in movement_rows}
    assert movement_types.issubset(
        {"CONSUMPTION", "RESERVATION", "DISPOSAL", "RETURN", "REQUEST"}
    )

    duplicate_requesters = db.execute_query(
        """
        SELECT requester_type, name, COUNT(*) AS c
        FROM Requesters
        GROUP BY requester_type, name
        HAVING COUNT(*) > 1
        """
    )
    assert not duplicate_requesters

    activity_count = db.execute_query("SELECT COUNT(*) AS c FROM Activity_Log")[0]["c"]
    assert activity_count > 0

    admin_rows = db.execute_query(
        """
        SELECT COUNT(DISTINCT user_name) AS c
        FROM Activity_Log
        WHERE user_name IS NOT NULL AND TRIM(user_name) != ''
        """
    )
    assert admin_rows[0]["c"] >= 5

    required_activity_types = {
        "REQUESTER_ADDED",
        "ITEM_ADDED",
        "STOCK_RECEIVED",
        "REQUISITION_CREATED",
        "STOCK_ADJUSTED",
    }
    type_rows = db.execute_query("SELECT DISTINCT activity_type FROM Activity_Log")
    present_types = {row["activity_type"] for row in type_rows}
    assert required_activity_types.issubset(present_types)
