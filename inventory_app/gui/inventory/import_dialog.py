"""
Import dialog for inventory items.
Shows required headers and an example, allows user to select an Excel file (.xlsx), enter an editor name
for audit and perform import via `inventory_app.services.item_importer` service.

Uses background threading via QThreadPool to prevent UI freezes during import.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QHBoxLayout,
    QMessageBox,
    QGroupBox,
    QProgressBar,
)
from PyQt6.QtCore import pyqtSignal, QObject
from inventory_app.services.item_importer import import_items_from_excel
from inventory_app.gui.utils.worker import worker_pool, Worker
from inventory_app.utils.logger import logger


class ImportWorkerSignals(QObject):
    """Signals for import worker with progress updates."""

    progress = pyqtSignal(int, int, int)  # current, total, skipped
    result = pyqtSignal(object)
    error = pyqtSignal(tuple)
    finished = pyqtSignal()


class ImportWorker(Worker):
    """Worker for import with progress callback support."""

    def __init__(self, file_path: str, editor_name: str):
        # Don't call parent init, we handle everything ourselves
        super(Worker, self).__init__()
        self.file_path = file_path
        self.editor_name = editor_name
        self.signals = ImportWorkerSignals()
        self._is_cancelled = False

    def run(self):
        """Execute import with progress callbacks."""
        try:
            if self._is_cancelled:
                return

            def progress_callback(current: int, total: int, skipped: int):
                if not self._is_cancelled:
                    self.signals.progress.emit(current, total, skipped)

            imported_count, messages = import_items_from_excel(
                self.file_path,
                editor_name=self.editor_name,
                progress_callback=progress_callback,
            )

            if not self._is_cancelled:
                self.signals.result.emit(
                    {
                        "imported_count": imported_count,
                        "messages": messages,
                        "file_path": self.file_path,
                    }
                )
        except Exception as e:
            import traceback
            import sys

            logger.error(f"Import worker error: {e}")
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            if not self._is_cancelled:
                self.signals.finished.emit()

    def cancel(self):
        """Request cancellation."""
        self._is_cancelled = True


class ImportItemsDialog(QDialog):
    """Dialog to import items from an Excel file with async processing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Items from Excel")
        self.setModal(True)
        self.file_path = None
        self._current_worker: Optional[ImportWorker] = None
        self._is_importing = False
        self._build_ui()
        self.import_result = None

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        # Instruction Group
        info_group = QGroupBox("Import Instructions")
        info_layout = QVBoxLayout(info_group)
        intro = QLabel(
            "<b>Required:</b> Select an Excel (.xlsx) file with headers: <code>name</code>, <code>stocks</code>, <code>item type</code>."
        )
        intro.setWordWrap(True)
        info_layout.addWidget(intro)

        example = QLabel(
            "<b>Example headers:</b> <code>name | stocks | item type | category | size | brand | supplier | expiration date</code>"
        )
        example.setWordWrap(True)
        info_layout.addWidget(example)

        notes = QLabel(
            "Notes: Missing text values will be set to 'N/A'. Empty dates will be treated as 'N/A'. "
            "For consumables, unit-bearing stocks like '900ml' are auto-read as quantity 900 (size keeps '900ml'). "
            "Package entries like '1 box (100pcs)' are auto-read as quantity 100."
        )
        notes.setWordWrap(True)
        info_layout.addWidget(notes)
        layout.addWidget(info_group)

        # File chooser group
        file_group = QGroupBox("File")
        file_layout = QHBoxLayout(file_group)
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: gray;")
        choose_button = QPushButton("Choose file...")
        choose_button.clicked.connect(self._choose_file)
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(choose_button)
        layout.addWidget(file_group)

        # Editor information group
        editor_group = QGroupBox("Editor Information (Required)")
        editor_layout = QHBoxLayout(editor_group)
        editor_layout.addWidget(QLabel("Editor name/initials:"))
        self.editor_input = QLineEdit()
        self.editor_input.setPlaceholderText(
            "Enter your name or initials for audit trail..."
        )
        editor_layout.addWidget(self.editor_input, 1)
        layout.addWidget(editor_group)

        # Progress section
        progress_group = QGroupBox("Import Progress")
        progress_layout = QVBoxLayout(progress_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        # Status label showing current/total and skipped
        self.status_label = QLabel("Ready to import")
        self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
        progress_layout.addWidget(self.status_label)

        layout.addWidget(progress_group)

        # Buttons (bottom-right)
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        self.import_button = QPushButton("Import")
        self.import_button.clicked.connect(self._perform_import)
        self.import_button.setEnabled(False)
        self.import_button.setDefault(True)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel)
        buttons_layout.addWidget(self.import_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        # Make window fixed size for a consistent UI
        self.setFixedSize(600, 350)

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel file", "", "Excel Files (*.xlsx);;All Files (*)"
        )
        if path:
            self.file_path = path
            self.file_label.setText(path)
            self.import_button.setEnabled(True)

    def _perform_import(self):
        """Start import in background thread."""
        if not self.file_path:
            QMessageBox.warning(
                self, "No file", "Please select an Excel (.xlsx) file to import."
            )
            return

        if self._is_importing:
            return

        editor = self.editor_input.text().strip() or "Import"

        # Set importing state
        self._is_importing = True
        self._set_importing_state(True)
        self.status_label.setText("Starting import...")
        self.progress_bar.setValue(0)

        # Create custom import worker with progress support
        self._current_worker = ImportWorker(self.file_path, editor)
        self._current_worker.signals.progress.connect(self._on_progress)
        self._current_worker.signals.result.connect(self._on_import_complete)
        self._current_worker.signals.error.connect(self._on_import_error)
        self._current_worker.signals.finished.connect(self._on_import_finished)

        # Start worker
        worker_pool.start(self._current_worker)

    def _on_progress(self, current: int, total: int, skipped: int):
        """Handle progress update from worker (runs on main thread)."""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)

        # Update status label with format: [progress/total], skipped: X
        self.status_label.setText(f"[{current}/{total}], skipped: {skipped}")

    def _on_import_complete(self, result: dict):
        """Handle import complete (runs on main thread)."""
        imported_count = result["imported_count"]
        messages = result["messages"]
        file_path = result["file_path"]

        # Count skipped from messages
        skipped_count = sum(
            1 for m in messages if "skipping" in m.lower() or "failed" in m.lower()
        )

        # Update final status
        self.status_label.setText(
            f"Import complete! Imported: {imported_count}, Skipped: {skipped_count}"
        )
        self.progress_bar.setValue(100)

        QMessageBox.information(
            self,
            "Import finished",
            f"Successfully imported {imported_count} items.\nSkipped: {skipped_count} rows.",
        )
        self.import_result = (imported_count, messages)
        logger.info(f"Import dialog: imported {imported_count} rows from {file_path}")
        self.accept()

    def _on_import_error(self, error_tuple: tuple):
        """Handle import error (runs on main thread)."""
        exctype, value, tb = error_tuple
        error_msg = str(value)

        self.status_label.setText(f"Error: {error_msg[:50]}...")

        if exctype is ValueError or (
            exctype is not None and issubclass(exctype, ValueError)
        ):
            QMessageBox.critical(self, "Import failed", error_msg)
        else:
            logger.error(f"Unexpected import error: {value}\n{tb}")
            QMessageBox.critical(
                self, "Import failed", f"Unexpected error: {error_msg}"
            )

    def _on_import_finished(self):
        """Handle import finished (runs on main thread)."""
        self._is_importing = False
        self._current_worker = None
        self._set_importing_state(False)

    def _set_importing_state(self, is_importing: bool):
        """Update UI for importing state."""
        self.import_button.setEnabled(not is_importing and self.file_path is not None)
        self.cancel_button.setText("Cancel Import" if is_importing else "Cancel")

    def _on_cancel(self):
        """Handle cancel button click."""
        if self._is_importing and self._current_worker:
            # Cancel ongoing import
            self._current_worker.cancel()
            self.status_label.setText("Import cancelled by user.")
            self._is_importing = False
            self._set_importing_state(False)
        else:
            self.reject()
