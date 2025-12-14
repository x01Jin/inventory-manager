from inventory_app.gui.navigation import NavigationPanel
from inventory_app.gui.main_window import MainWindow


def test_navigation_has_help_button(qtbot):
    nav = NavigationPanel()
    # Find a button that contains the word 'Help'
    texts = [b.text() for b in nav.nav_buttons]
    assert any("Help" in t for t in texts)


def test_mainwindow_includes_help_page(qtbot):
    window = MainWindow()
    # The help page should be the last (index 6)
    assert window.content_stack.count() >= 7
    # Basic check that the widget at index 6 has the expected attribute
    help_widget = window.content_stack.widget(6)
    assert hasattr(help_widget, "load_current_tab")
    # Should expose a tab widget for different help sections
    assert hasattr(help_widget, "tab_widget")


def test_helppage_tabs_exist_and_load(qtbot):
    from inventory_app.gui.help.help_page import HelpPage

    hp = HelpPage()
    # Expect the 6 tabs we configured
    expected = {
        "General",
        "Dashboard",
        "Inventory",
        "Requisitions",
        "Requesters",
        "Settings",
    }
    tabs = {hp.tab_widget.tabText(i) for i in range(hp.tab_widget.count())}
    assert expected <= tabs

    # Try loading each tab's content (should not raise)
    for i in range(hp.tab_widget.count()):
        hp.tab_widget.setCurrentIndex(i)
        hp.load_current_tab()
        viewer = hp.viewers[hp.tab_widget.tabText(i)]
        assert viewer.toPlainText() or viewer.toHtml()
