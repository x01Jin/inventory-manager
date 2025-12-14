from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextBrowser, QTabWidget

from inventory_app.gui.styles import DarkTheme


class HelpPage(QWidget):
    """Help page that displays the instruction manual (markdown)."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Help & Instructions")
        header.setStyleSheet(
            f"font-size: {DarkTheme.FONT_SIZE_TITLE}pt; font-weight: bold; color: {DarkTheme.TEXT_PRIMARY};"
        )
        layout.addWidget(header)

        # Buttons removed: Refresh / Open in Editor (not needed in-app)

        # Tabbed viewers for different help sections
        self.tab_widget = QTabWidget()
        self.viewers: dict[str, QTextBrowser] = {}
        # Map tab display name -> filename in docs/
        self.filename_map: dict[str, str] = {
            # Prefer package-local help files (packaged with PyInstaller)
            "General": "help-general.md",
            "Dashboard": "help-dashboard.md",
            "Inventory": "help-inventory.md",
            "Requisitions": "help-requisitions.md",
            "Requesters": "help-requesters.md",
            "Reports": "help-reports.md",
            "Settings": "help-settings.md",
        }

        for title in self.filename_map.keys():
            page = QWidget()
            page_layout = QVBoxLayout(page)
            viewer = QTextBrowser()
            viewer.setOpenExternalLinks(True)
            viewer.setStyleSheet(
                f"color: {DarkTheme.TEXT_SECONDARY}; background-color: {DarkTheme.PRIMARY_DARK}; padding: 10px;"
            )
            page_layout.addWidget(viewer)
            self.tab_widget.addTab(page, title)
            self.viewers[title] = viewer

        layout.addWidget(self.tab_widget, 1)

        # No external controls to connect

        # Load the initially selected tab
        self.load_current_tab()

        # Refresh tab content when the user switches tabs
        self.tab_widget.currentChanged.connect(lambda _: self.load_current_tab())

    def _find_manual_path(self) -> Path | None:
        # Try to locate the docs/instruction-manual.md file relative to package root
        import sys

        candidates: list[Path] = []
        # Project layout during development: repo root/docs/instruction-manual.md
        try:
            base = Path(__file__).resolve().parents[3]
            candidates.append(base / "docs" / "instruction-manual.md")
        except Exception:
            pass

        # If packaged with PyInstaller the extracted temp folder is in sys._MEIPASS
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "docs" / "instruction-manual.md")

        # Also check the current working directory (useful when running the EXE beside docs/)
        candidates.append(Path.cwd() / "docs" / "instruction-manual.md")

        for candidate in candidates:
            if candidate and candidate.exists():
                return candidate

        return None

    def _resolve_manual_file(self, filename: str) -> Path | None:
        """Resolve a markdown file from several likely locations (repo, packaged, cwd)."""
        import sys

        candidates: list[Path] = []
        # First check package-local help dir (same folder as this module)
        candidates.append(Path(__file__).resolve().parent / filename)
        try:
            base = Path(__file__).resolve().parents[3]
            candidates.append(base / "docs" / filename)
        except Exception:
            pass

        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "docs" / filename)

        candidates.append(Path.cwd() / "docs" / filename)

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def load_current_tab(self):
        """Load the markdown for the currently selected tab into its viewer."""
        current_title = self.tab_widget.tabText(self.tab_widget.currentIndex())
        viewer = self.viewers.get(current_title)
        if viewer is None:
            return

        filename = self.filename_map.get(current_title)
        if not filename:
            viewer.setPlainText("No help file configured for this tab.")
            return

        path = self._resolve_manual_file(filename)
        if not path:
            viewer.setPlainText(f"Help file not found: docs/{filename}")
            return

        try:
            import markdown  # type: ignore[import-not-found]

            text = path.read_text(encoding="utf-8")
            html = markdown.markdown(text, extensions=["fenced_code", "tables"])
            wrapped = f'<div style="font-family: "Courier New", monospace; color: {DarkTheme.TEXT_SECONDARY}; padding: 16px;">{html}</div>'
            viewer.setHtml(wrapped)
        except Exception:
            viewer.setPlainText(path.read_text(encoding="utf-8"))

    def load_manual(self):
        """Load and render the manual. Falls back to a short message if not found."""
        # Legacy method removed; use `load_current_tab()` instead.
        raise RuntimeError("load_manual() is deprecated; use load_current_tab()")

    def open_manual_in_editor(self):
        current_title = self.tab_widget.tabText(self.tab_widget.currentIndex())
        filename = self.filename_map.get(current_title)
        if not filename:
            return
        path = self._resolve_manual_file(filename)
        if not path:
            return
        try:
            os.startfile(str(path))
        except Exception:
            import webbrowser

            webbrowser.open(path.as_uri())

    def open_current_in_editor(self):
        """Compatibility wrapper used by the button connection."""
        return self.open_manual_in_editor()
