import pytest
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QLabel, QTableWidget, QTabWidget
from inventory_app.gui.dashboard.activity import ActivityManager
from inventory_app.gui.dashboard.alerts import AlertsManager
from inventory_app.gui.dashboard.dashboard_page import DashboardPage
from inventory_app.gui.styles import DarkTheme


@pytest.fixture
def mock_metrics(monkeypatch):
    """Mock metrics data for UI tests."""
    metrics = {
        "total_items": 120,
        "total_stock": 1000,
        "recent_adds": 5,
        "low_stock": 5,
        "expiring_soon": 2,
        "ongoing_reqs": 3,
        "requested_reqs": 1,
        "active_reqs": 1,
        "overdue_reqs": 1,
    }
    monkeypatch.setattr(
        "inventory_app.gui.dashboard.dashboard_page.get_consolidated_metrics",
        lambda: metrics,
    )
    return metrics


def test_dashboard_initialization(qtbot, mock_metrics):
    """Verify that the dashboard page initializes and shows metrics."""
    page = DashboardPage()
    qtbot.addWidget(page)

    # Wait for metrics to load (async)
    import time

    timeout = 5
    start = time.time()
    while page._metrics_worker is not None and time.time() - start < timeout:
        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()
        time.sleep(0.1)

    # Check if metric values from mock are displayed in the labels
    # We need to find the specific labels created by MetricsManager
    # Based on MetricsManager implementation, they might have specific names or text
    assert page.metrics_manager is not None

    # Verify specific metric value display
    # We find children by type or name if known
    labels = page.findChildren(QLabel)
    total_items_val = str(mock_metrics["total_items"])
    assert any(total_items_val in label.text() for label in labels)


def test_dashboard_alerts_widget(qtbot):
    """Verify that the alerts widget exists on the dashboard."""
    page = DashboardPage()
    qtbot.addWidget(page)

    # Check for alerts list or table
    # Standard dashboard usually has an alerts section
    assert (
        hasattr(page, "alerts_table") or page.findChild(QWidget, "alerts") is not None
    )


def test_dashboard_alerts_has_full_tab(qtbot):
    """Dashboard alerts section should expose Summary and All Alerts tabs."""
    page = DashboardPage()
    qtbot.addWidget(page)

    tab_widgets = page.findChildren(QTabWidget)
    assert tab_widgets

    alerts_tabs = None
    for tabs in tab_widgets:
        titles = {tabs.tabText(i) for i in range(tabs.count())}
        if {"Summary", "All Alerts"}.issubset(titles):
            alerts_tabs = tabs
            break

    assert alerts_tabs is not None
    assert isinstance(page.all_alerts_table, QTableWidget)


def test_activity_log_display(qtbot):
    """Verify that the activity log is present on the dashboard."""
    page = DashboardPage()
    qtbot.addWidget(page)

    # Check for activity log widget
    assert (
        hasattr(page, "activity_text")
        or page.findChild(QWidget, "activity_log") is not None
    )


def test_latest_activity_height_expands_for_long_description(qtbot):
    """Latest Activity table should grow vertically for wrapped long text."""
    manager = ActivityManager()
    widget = manager.create_activity_widget()
    qtbot.addWidget(widget)

    latest_table = manager.latest_table.findChild(QTableWidget)
    assert latest_table is not None

    activities = [
        {
            "description": "Merged suppliers into RNJ Medical Equipment: "
            + ", ".join(["RNJ Medical Equipment"] * 8)
            + " (updated 14 item(s))",
            "user": "tester",
            "time": None,
        }
    ]

    manager._populate_table(manager.latest_table, activities)

    assert latest_table.rowCount() == 1
    assert latest_table.rowHeight(0) > 20
    assert latest_table.maximumHeight() > manager.LATEST_ACTIVITY_MIN_HEIGHT


def test_dashboard_shows_progressive_loading_status(qtbot, monkeypatch):
    """Dashboard should track staged loading progress and reach ready state."""

    monkeypatch.setattr(
        DashboardPage,
        "_load_metrics_async",
        lambda self, cycle_id: self._mark_section_complete(cycle_id, "metrics"),
    )
    monkeypatch.setattr(
        DashboardPage,
        "_load_activity_async",
        lambda self, cycle_id: self._mark_section_complete(cycle_id, "activity"),
    )
    monkeypatch.setattr(
        DashboardPage,
        "_load_alerts_async",
        lambda self, cycle_id: self._mark_section_complete(cycle_id, "alerts"),
    )
    monkeypatch.setattr(
        DashboardPage,
        "_load_schedule_async",
        lambda self, cycle_id: self._mark_section_complete(cycle_id, "schedule"),
    )

    page = DashboardPage()
    qtbot.addWidget(page)

    assert page._load_completed == page._load_total
    assert page.dashboard_loading_status.text() == "Dashboard ready"


def test_dashboard_alert_status_cells_keep_highlight_colors(qtbot):
    """Summary and full alerts tables should preserve critical/warning highlight colors."""
    manager = AlertsManager()

    summary = manager.create_alerts_table()
    full = manager.create_full_alerts_table()
    qtbot.addWidget(summary)
    qtbot.addWidget(full)

    alerts_data = [
        {
            "type": "expired",
            "item": "Hydrochloric Acid",
            "status": "Critical",
            "days_until": -1,
            "due_date": "01/01/2024",
            "category": "Chemicals-Liquid",
            "batch": "B1",
        },
        {
            "type": "expiring",
            "item": "Sodium Chloride",
            "status": "Warning",
            "days_until": 5,
            "due_date": "01/01/2027",
            "category": "Chemicals-Solid",
            "batch": "B2",
        },
    ]

    manager.populate_alerts_table(summary, alerts_data)
    manager.populate_full_alerts_table(full, alerts_data)

    critical_summary_item = summary.item(0, 2)
    warning_full_item = full.item(1, 6)

    assert critical_summary_item is not None
    assert warning_full_item is not None
    assert critical_summary_item.background().color() == QColor(DarkTheme.ERROR_COLOR)
    assert warning_full_item.background().color() == QColor(DarkTheme.WARNING_COLOR)


def test_dashboard_full_alerts_populates_incrementally(qtbot, monkeypatch):
    """Full alerts table should grow in batches, not preallocate all rows at once."""
    manager = AlertsManager()
    table = manager.create_full_alerts_table()
    qtbot.addWidget(table)

    row_count_calls = []
    original_set_row_count = table.setRowCount

    def tracking_set_row_count(count: int):
        row_count_calls.append(count)
        original_set_row_count(count)

    monkeypatch.setattr(table, "setRowCount", tracking_set_row_count)

    alerts_data = [
        {
            "type": "expired",
            "item": f"Item {idx}",
            "status": "Critical" if idx % 2 == 0 else "Warning",
            "days_until": -idx,
            "due_date": "01/01/2024",
            "category": "Consumables",
            "batch": "-",
        }
        for idx in range(180)
    ]

    manager.populate_full_alerts_table(table, alerts_data)

    qtbot.waitUntil(lambda: table.rowCount() == len(alerts_data), timeout=5000)

    assert row_count_calls
    assert row_count_calls[0] == 0
    assert len(row_count_calls) > 2


def test_dashboard_full_alerts_item_column_uses_content_width(qtbot):
    """All Alerts Item column should size to cell content, not stretch."""
    manager = AlertsManager()
    table = manager.create_full_alerts_table()
    qtbot.addWidget(table)

    header = table.horizontalHeader()
    assert header is not None
    assert header.sectionResizeMode(1) == header.ResizeMode.ResizeToContents
