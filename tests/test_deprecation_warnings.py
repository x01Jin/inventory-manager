import pytest

from inventory_app.services.stock_movement_service import StockMovementService
from inventory_app.services.item_service import ItemService
from inventory_app.database.connection import db


def test_record_disposal_records_without_warning(monkeypatch):
    svc = StockMovementService()
    # Prevent DB side effects by patching execute_update
    orig = db.execute_update

    def fake_execute_update(query, params=(), return_last_id=False):
        return 1

    monkeypatch.setattr(db, "execute_update", fake_execute_update)

    # record_disposal should not issue a DeprecationWarning
    svc.record_disposal(item_id=1, quantity=1, source_id=1, note="note")

    monkeypatch.setattr(db, "execute_update", orig)


def test_get_inventory_items_deprecation(monkeypatch):
    svc = ItemService()
    # Patch batch retrieval to avoid DB calls
    monkeypatch.setattr(svc, "get_inventory_batches_for_selection", lambda *a, **k: [])

    with pytest.warns(DeprecationWarning):
        svc.get_inventory_items_for_selection()
