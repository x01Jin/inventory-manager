from inventory_app.services.stock_movement_service import StockMovementService
from inventory_app.services.movement_types import MovementType


def test_get_reserved_stock_query_parameterized(monkeypatch):
    service = StockMovementService()
    captured = {"query": None, "params": None}

    def fake_execute_query(query, params=None):
        captured["query"] = query
        captured["params"] = params
        return [{"reserved_qty": 5}]

    import inventory_app.database.connection as conn

    monkeypatch.setattr(conn.db, "execute_query", fake_execute_query)

    qty = service.get_reserved_stock(123)
    # Returned qty should match our fake result
    assert qty == 5
    # Ensure no legacy `%s` is present
    assert captured["query"] is not None
    assert "%s" not in captured["query"]
    # Ensure the movement_type IN clause uses ? placeholders
    q_no_spaces = captured["query"].replace(" ", "")
    assert "movement_typeIN(?,?)" in q_no_spaces
    # Ensure params forwarded in the right order
    assert captured["params"] == (
        123,
        MovementType.RESERVATION.value,
        MovementType.REQUEST.value,
    )
