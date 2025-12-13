from pathlib import Path
from inventory_app.gui.reports.report_config import ReportConfig


def test_reports_page_uses_reportconfig_labels():
    # Read source and ensure centralized labels are used in reports_page.py
    file_path = Path("inventory_app/gui/reports/reports_page.py")
    text = file_path.read_text(encoding="utf-8")
    # Ensure that the reports page references the central labels in ReportConfig
    for key in ReportConfig.LABELS.keys():
        assert f'ReportConfig.LABELS["{key}"]' in text


def test_trends_granularity_tooltip_present():
    file_path = Path("inventory_app/gui/reports/reports_page.py")
    text = file_path.read_text(encoding="utf-8")
    # Ensure that the tooltip setting references the ReportConfig constant
    assert "setToolTip(ReportConfig.GRANULARITY_TOOLTIP)" in text


def test_trends_granularity_has_auto_option():
    file_path = Path("inventory_app/gui/reports/reports_page.py")
    text = file_path.read_text(encoding="utf-8")
    # Trends page should include an 'Auto' option for granularity
    assert '["Auto",' in text
