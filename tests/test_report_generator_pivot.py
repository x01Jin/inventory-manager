from datetime import date

from inventory_app.gui.reports.report_generator import ReportGenerator
from inventory_app.gui.reports.query_builder import ReportQueryBuilder


def test_pivots_normalized_rows(monkeypatch):
    # Prepare a normalized-style response: base columns + PERIOD and PERIOD_QUANTITY
    rows = [
        {
            "ITEMS": "Pencil",
            "CATEGORIES": "Stationery",
            "ACTUAL_INVENTORY": 10,
            "SIZE": "N/A",
            "BRAND": "Acme",
            "OTHER SPECIFICATIONS": "",
            "PERIOD": "2023-01-01",
            "PERIOD_QUANTITY": 2,
        },
        {
            "ITEMS": "Pencil",
            "CATEGORIES": "Stationery",
            "ACTUAL_INVENTORY": 10,
            "SIZE": "N/A",
            "BRAND": "Acme",
            "OTHER SPECIFICATIONS": "",
            "PERIOD": "2023-01-02",
            "PERIOD_QUANTITY": 3,
        },
        {
            "ITEMS": "Eraser",
            "CATEGORIES": "Stationery",
            "ACTUAL_INVENTORY": 5,
            "SIZE": "N/A",
            "BRAND": "RubberCorp",
            "OTHER SPECIFICATIONS": "",
            "PERIOD": "2023-01-01",
            "PERIOD_QUANTITY": 1,
        },
    ]

    generator = ReportGenerator()
    start = date(2023, 1, 1)
    end = date(2023, 1, 2)

    # Monkeypatch the query builder's execute_report_query to return our normalized rows
    monkeypatch.setattr(
        ReportQueryBuilder,
        "execute_report_query",
        lambda self, q, p: rows,
    )
    # Also patch build_dynamic_report_query to return a dummy query
    monkeypatch.setattr(
        ReportQueryBuilder,
        "build_dynamic_report_query",
        lambda self, *a, **k: ("", ()),
    )

    # Call the generator; pivoting should occur when PERIOD keys exist
    result = generator._get_dynamic_report_data(start, end, "daily")

    # Ensure pivoted result contains two items with expected period columns
    assert any(r["ITEMS"] == "Pencil" for r in result)
    pencil_row = next(r for r in result if r["ITEMS"] == "Pencil")
    assert pencil_row["2023-01-01"] == 2
    assert pencil_row["2023-01-02"] == 3
    assert pencil_row["TOTAL QUANTITY"] == 5


def test_build_dynamic_report_query_large_range_uses_cte():
    builder = ReportQueryBuilder()
    start = date(2023, 1, 1)
    end = date(2023, 12, 31)
    query, params = builder.build_dynamic_report_query(start, end, "daily")
    # Large range should use a CTE periods with parameterized VALUES
    assert "WITH periods" in query
    assert "p.period_key" in query or "p.start" in query


def test_pivot_sums_duplicate_rows(monkeypatch):
    rows = [
        {
            "ITEMS": "Glue",
            "CATEGORIES": "Stationery",
            "ACTUAL_INVENTORY": 20,
            "SIZE": "N/A",
            "BRAND": "StickCo",
            "OTHER SPECIFICATIONS": "",
            "PERIOD": "2023-01-01",
            "PERIOD_QUANTITY": 1,
        },
        {
            "ITEMS": "Glue",
            "CATEGORIES": "Stationery",
            "ACTUAL_INVENTORY": 20,
            "SIZE": "N/A",
            "BRAND": "StickCo",
            "OTHER SPECIFICATIONS": "",
            "PERIOD": "2023-01-01",
            "PERIOD_QUANTITY": 2,
        },
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

    result = generator._get_dynamic_report_data(start, end, "daily")
    glue_row = next(r for r in result if r["ITEMS"] == "Glue")
    assert glue_row["2023-01-01"] == 3
    assert glue_row["TOTAL QUANTITY"] == 3
