from inventory_app.gui.reports.report_worker import ReportWorker
from inventory_app.gui.reports.report_generator import report_generator


def test_report_worker_passes_filters(monkeypatch):
    captured = {}

    def fake_generate_report(
        start_date,
        end_date,
        output_path=None,
        category_filter=None,
        supplier_filter=None,
        include_consumables=True,
        show_individual_only=False,
        structured=False,
    ):
        captured["category_filter"] = category_filter
        captured["supplier_filter"] = supplier_filter
        captured["show_individual_only"] = show_individual_only
        return "fake_path.xlsx"

    monkeypatch.setattr(report_generator, "generate_report", fake_generate_report)

    rw = ReportWorker(
        "usage",
        "2025-01-01",
        "2025-01-31",
        category_filter="CAT-A",
        supplier_filter="SUP-X",
    )
    result = rw._generate_usage_report()
    assert result == "fake_path.xlsx"
    assert captured["category_filter"] == "CAT-A"
    assert captured["supplier_filter"] == "SUP-X"
    assert not captured["show_individual_only"]
