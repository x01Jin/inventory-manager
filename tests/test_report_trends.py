from datetime import date

from inventory_app.gui.reports.report_generator import ReportGenerator
from inventory_app.gui.reports.query_builder import ReportQueryBuilder


def test_trends_aggregate_by_category(monkeypatch):
    # Simulate pivoted rows (ITEMS-level pivot) for two items in same category
    rows = [
        {
            "ITEMS": "Pencil",
            "CATEGORIES": "Stationery",
            "ACTUAL_INVENTORY": 10,
            "SIZE": "N/A",
            "BRAND": "Acme",
            "OTHER SPECIFICATIONS": "",
            "2023-01-01": 2,
            "2023-01-02": 3,
            "TOTAL QUANTITY": 5,
        },
        {
            "ITEMS": "Eraser",
            "CATEGORIES": "Stationery",
            "ACTUAL_INVENTORY": 5,
            "SIZE": "N/A",
            "BRAND": "RubberCorp",
            "OTHER SPECIFICATIONS": "",
            "2023-01-01": 1,
            "2023-01-02": 0,
            "TOTAL QUANTITY": 1,
        },
    ]

    generator = ReportGenerator()
    start = date(2023, 1, 1)
    end = date(2023, 1, 2)

    # Monkeypatch query builder to return these rows
    monkeypatch.setattr(
        ReportQueryBuilder,
        "execute_report_query",
        lambda self, q, p: rows,
    )
    monkeypatch.setattr(
        ReportQueryBuilder,
        "build_dynamic_report_query",
        lambda self, *a, **k: ("", ()),
    )

    result = generator._get_trends_data(start, end, "daily", group_by="category")
    assert len(result) == 1
    stationery = result[0]
    assert stationery["CATEGORIES"] == "Stationery"
    assert stationery["2023-01-01"] == 3
    assert stationery["2023-01-02"] == 3
    assert stationery["TOTAL QUANTITY"] == 6


def test_trends_top_n_filters(monkeypatch):
    rows = [
        {"ITEMS": "A", "CATEGORIES": "X", "TOTAL QUANTITY": 100, "2023-01-01": 100},
        {"ITEMS": "B", "CATEGORIES": "X", "TOTAL QUANTITY": 50, "2023-01-01": 50},
        {"ITEMS": "C", "CATEGORIES": "Y", "TOTAL QUANTITY": 20, "2023-01-01": 20},
    ]

    generator = ReportGenerator()
    start = date(2023, 1, 1)
    end = date(2023, 1, 1)

    monkeypatch.setattr(
        ReportQueryBuilder,
        "execute_report_query",
        lambda self, q, p: rows,
    )
    monkeypatch.setattr(
        ReportQueryBuilder,
        "build_dynamic_report_query",
        lambda self, *a, **k: ("", ()),
    )

    result = generator._get_trends_data(start, end, "daily", group_by="item", top_n=2)
    assert len(result) == 2
    assert result[0]["ITEMS"] == "A"
    assert result[1]["ITEMS"] == "B"


def test_trends_auto_granularity(monkeypatch):
    generator = ReportGenerator()
    start = date(2023, 1, 1)
    end = date(2023, 1, 15)

    # Monkeypatch the generator granularity function to return 'weekly'
    monkeypatch.setattr(generator, "get_granularity", lambda s, e: "weekly")

    called = {}

    def fake_get_trends_data(start_date, end_date, granularity, **kwargs):
        called["gran"] = granularity
        return []

    monkeypatch.setattr(generator, "_get_trends_data", fake_get_trends_data)

    # Call with granularity = 'auto' so generator computes vertically
    result = generator.generate_trends_report(start, end, granularity="auto")
    # Ensure the underlying method was called with our computed 'weekly'
    assert called.get("gran") == "weekly"
    # Generator should return an error string because there's no data
    assert "Failed to generate trends report" in result
    assert "No data found" in result
