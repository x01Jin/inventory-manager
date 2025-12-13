from inventory_app.gui.inventory.inventory_controller import InventoryController


def test_load_inventory_data_formats_query(monkeypatch):
    captured = {"query": None}

    def fake_execute_query(query, params=None):
        captured["query"] = query
        return []

    # Patch the database execute_query to capture the query and avoid DB dependency
    import inventory_app.database.connection as conn

    monkeypatch.setattr(conn.db, "execute_query", fake_execute_query)

    controller = InventoryController()
    rows = controller.load_inventory_data()

    assert rows == []
    # Ensure we captured a query string
    assert captured["query"] is not None
    # Ensure there are no leftover '%s' placeholders in the final query
    assert "%s" not in captured["query"]
