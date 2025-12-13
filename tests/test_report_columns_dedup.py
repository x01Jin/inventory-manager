from datetime import date, timedelta
from inventory_app.gui.reports.query_builder import ReportQueryBuilder
from inventory_app.gui.reports.columns import (
    report_base_columns_sql,
    inventory_base_columns_sql,
)


def test_report_query_includes_shared_report_columns():
    builder = ReportQueryBuilder()
    start = date.today() - timedelta(days=30)
    end = date.today()
    query, params = builder.build_dynamic_report_query(start, end, "monthly")
    # Ensure the generated query includes the shared base columns
    assert "ITEMS" in query
    assert report_base_columns_sql().split(",")[0].strip().split()[0] in query


def test_stock_levels_query_uses_inventory_base_columns(monkeypatch):
    captured = {"query": None, "params": None}

    def fake_execute_query(query, params=None):
        captured["query"] = query
        captured["params"] = params
        return []

    import inventory_app.database.connection as conn

    monkeypatch.setattr(conn.db, "execute_query", fake_execute_query)
    from inventory_app.gui.reports.data_sources import get_stock_levels_data

    _ = get_stock_levels_data()
    assert captured["query"] is not None
    # Assert inventory base columns SQL is present
    assert (
        "Item Name" in captured["query"]
        or inventory_base_columns_sql().split(",")[0].strip().split()[0]
        in captured["query"]
    )
