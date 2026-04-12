from datetime import date
from openpyxl import load_workbook
from inventory_app.gui.reports.reports_page import ReportsPage
from inventory_app.gui.reports.excel_utils import create_excel_report


def test_reports_page_filters(qtbot):
    """Verify that report filters behave correctly."""
    page = ReportsPage()
    qtbot.addWidget(page)

    # Switch to Usage by Grade Level report first to make filters visible
    idx_report = page.usage_report_type.findData("grade_level")
    page.usage_report_type.setCurrentIndex(idx_report)

    # Check default filter state within that report type
    assert page.usage_filter_type_combo.itemText(0) == "All Grades & Sections"
    assert page.usage_filter_value_combo.isHidden()

    # Switch to Grade Level filter
    idx = page.usage_filter_type_combo.findText("Grade Level")
    page.usage_filter_type_combo.setCurrentIndex(idx)
    assert not page.usage_filter_value_combo.isHidden()
    assert page.usage_filter_value_combo.itemText(0) == "All Grades"


def test_excel_report_ux_features(tmp_path):
    """Verify that generated Excel reports have correct UX features (freeze, filters)."""
    data = [{"Item": "Test Item", "Total Quantity": 10}]
    out = tmp_path / "report.xlsx"
    create_excel_report(data, out, "Test UI Report", date(2025, 1, 1), date(2025, 1, 2))

    wb = load_workbook(out)
    ws = wb.active
    assert ws is not None

    # Verify freeze panes (A5 is standard for our reports Header at 4)
    assert ws.freeze_panes == "A5"
    assert ws.auto_filter.ref.startswith("A4")

    # Total row check
    total_row = 5 + len(data)
    assert ws.cell(row=total_row, column=1).value == "Total"


def test_excel_report_column_width_accounts_for_data_content(tmp_path):
    """Column widths should account for long data values, not header text only."""
    long_name = "Sodium Bicarbonate Analytical Grade Very Long Label"
    data = [{"Item": long_name, "Total Quantity": 12}]
    out = tmp_path / "report_width.xlsx"

    create_excel_report(data, out, "Width Test", date(2025, 1, 1), date(2025, 1, 2))

    wb = load_workbook(out)
    ws = wb.active
    assert ws is not None

    # Column A should expand beyond baseline minimum because of long item text.
    assert ws.column_dimensions["A"].width > 20


def test_reports_centralized_labels():
    """Verify that reports page uses centralized ReportConfig labels."""
    from pathlib import Path

    page_source = Path("inventory_app/gui/reports/reports_page.py").read_text(
        encoding="utf-8"
    )

    # Ensure tooltips and labels reference ReportConfig constants
    assert "ReportConfig.GRANULARITY_TOOLTIP" in page_source
    assert "ReportConfig.LABELS" in page_source
