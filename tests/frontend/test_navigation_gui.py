from inventory_app.gui.navigation import NavigationPanel
from inventory_app.gui.main_window import MainWindow
from inventory_app.gui.help.help_page import HelpPage


def test_navigation_panel_structure(qtbot):
    """Verify that the navigation panel contains expected buttons."""
    nav = NavigationPanel()
    qtbot.addWidget(nav)

    texts = [b.text() for b in nav.nav_buttons]
    assert any("Dashboard" in t for t in texts)
    assert any("Inventory" in t for t in texts)
    assert any("Help" in t for t in texts)


def test_main_window_navigation(qtbot):
    """Verify that the main window has the correct pages in its stack."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Check if stack is populated (Min 7: Dash, Inv, Req, Reqr, Rep, Set, Help)
    assert window.content_stack.count() >= 7

    # Verify help page is accessible (usually the last page)
    help_widget = window.content_stack.widget(6)
    assert isinstance(help_widget, HelpPage)


def test_help_page_tabs_and_content(qtbot):
    """Verify that the help page loads all required documentation tabs."""
    hp = HelpPage()
    qtbot.addWidget(hp)

    expected_tabs = {
        "General",
        "Dashboard",
        "Inventory",
        "Requisitions",
        "Requesters",
        "Settings",
    }
    actual_tabs = {hp.tab_widget.tabText(i) for i in range(hp.tab_widget.count())}

    assert expected_tabs <= actual_tabs

    # Verify content loading for the first tab
    hp.tab_widget.setCurrentIndex(0)
    hp.load_current_tab()
    tab_name = hp.tab_widget.tabText(0)
    viewer = hp.viewers[tab_name]
    assert viewer.toPlainText() or viewer.toHtml()


def test_main_window_reports_refresh_targets_reports_page(qtbot, monkeypatch):
    """Reports page refresh should call reports page hook, not help page hook."""
    window = MainWindow()
    qtbot.addWidget(window)

    reports_calls = []
    help_calls = []

    monkeypatch.setattr(
        window.reports_page, "refresh_data", lambda: reports_calls.append(1)
    )
    monkeypatch.setattr(
        window.help_page, "load_current_tab", lambda: help_calls.append(1)
    )

    window._refresh_page_data(4)

    assert len(reports_calls) == 1
    assert len(help_calls) == 0


def test_main_window_help_refresh_targets_help_page(qtbot, monkeypatch):
    """Help page refresh should trigger help tab reload on help index."""
    window = MainWindow()
    qtbot.addWidget(window)

    help_calls = []
    monkeypatch.setattr(
        window.help_page, "load_current_tab", lambda: help_calls.append(1)
    )

    window._refresh_page_data(6)

    assert len(help_calls) == 1
