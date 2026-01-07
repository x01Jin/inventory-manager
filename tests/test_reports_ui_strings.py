from pathlib import Path
from inventory_app.gui.reports.report_config import ReportConfig


def test_reports_page_uses_reportconfig_labels():
    # Read source and ensure centralized labels are used in reports_page.py
    file_path = Path("inventory_app/gui/reports/reports_page.py")
    text = file_path.read_text(encoding="utf-8")
    # Check for labels that are actually used in the reports page
    # Note: Some labels like "supplier" are not used in reports_page anymore after v0.7.0b patches
    used_labels = ["group_by", "top_items"]  # Labels actually used in trends tab
    for key in used_labels:
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
