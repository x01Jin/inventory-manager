import pytest
from datetime import datetime

import inventory_app.database.connection as conn
from inventory_app.database.models import Requisition


def _make_bad_row(**overrides):
    base = {
        "id": 1,
        "requester_id": 1,
        "expected_request": "2025-12-10T09:00:00",
        "expected_return": "2025-12-20T10:00:00",
        "status": "requested",
        "lab_activity_name": "Test Activity",
        "lab_activity_description": None,
        "lab_activity_date": "2025-12-10",
        "num_students": None,
        "num_groups": None,
        "created_at": datetime.now().isoformat(),
    }
    base.update(overrides)
    return base


def test_get_all_raises_on_invalid_expected_request(monkeypatch):
    bad_row = _make_bad_row(expected_request="not-a-date")

    def fake_execute_query(query, params=()):
        return [bad_row]

    monkeypatch.setattr(conn.db, "execute_query", fake_execute_query)

    with pytest.raises(ValueError) as excinfo:
        Requisition.get_all()

    assert "expected_request" in str(excinfo.value)


def test_get_all_raises_on_invalid_lab_activity_date(monkeypatch):
    bad_row = _make_bad_row(lab_activity_date="not-a-date")

    def fake_execute_query(query, params=()):
        return [bad_row]

    monkeypatch.setattr(conn.db, "execute_query", fake_execute_query)

    with pytest.raises(ValueError) as excinfo:
        Requisition.get_all()

    assert "lab_activity_date" in str(excinfo.value)
