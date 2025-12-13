from datetime import date

from inventory_app.gui.reports.report_generator import ReportGenerator


def test_format_excel_headers_translates_and_parses_period_keys():
    gen = ReportGenerator()

    start = date(2023, 1, 1)
    end = date(2023, 1, 3)

    headers = [
        "ITEMS",
        "CATEGORIES",
        "2023-01-01",
        "TOTAL QUANTITY",
        "Item Name",
        "Current Stock",
    ]

    formatted = gen._format_excel_headers(headers, start, end)

    # Mapped titles
    assert "Item" in formatted
    assert "Category" in formatted
    assert "Total Quantity" in formatted
    assert "Current Stock" in formatted

    # Daily header parsing (for 2023-01-01) should produce a human readable fragment
    assert any("Jan" in str(h) or "2023" in str(h) for h in formatted)


def test_format_excel_headers_respects_manual_granularity():
    gen = ReportGenerator()

    start = date(2023, 1, 1)
    end = date(2023, 1, 7)

    # Date range implies 'daily' via smart granularity, but we force 'monthly'
    headers = ["2023-01", "ITEMS"]

    # Explicitly pass monthly granularity
    formatted = gen._format_excel_headers(headers, start, end, granularity="monthly")

    # When forced to monthly, the '2023-01' header should be parsed as a monthly header
    assert any("Jan" in str(h) for h in formatted)
