"""
Import dialog for inventory items.
Shows required headers and an example, allows user to select an Excel file (.xlsx), enter an editor name
for audit and perform import via `inventory_app.services.item_importer` service.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QTextEdit,
    QHBoxLayout,
    QMessageBox,
    QGroupBox,
)
from inventory_app.services.item_importer import import_items_from_excel
from inventory_app.utils.logger import logger


class ImportItemsDialog(QDialog):
    """Dialog to import items from an Excel file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Items from Excel")
        self.setModal(True)
        self.file_path = None
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
            "Notes: Missing text values will be set to 'N/A'. Empty dates will be treated as 'N/A'."
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

        # Output / log group
        log_group = QGroupBox("Import Log")
        log_layout = QVBoxLayout(log_group)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFixedHeight(160)
        log_layout.addWidget(self.output)
        layout.addWidget(log_group)

        # Buttons (bottom-right)
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        self.import_button = QPushButton("Import")
        self.import_button.clicked.connect(self._perform_import)
        self.import_button.setEnabled(False)
        self.import_button.setDefault(True)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(self.import_button)
        buttons_layout.addWidget(cancel)
        layout.addLayout(buttons_layout)

        # Make window fixed size for a consistent UI
        self.setFixedSize(600, 400)

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel file", "", "Excel Files (*.xlsx);;All Files (*)"
        )
        if path:
            self.file_path = path
            self.file_label.setText(path)
            self.import_button.setEnabled(True)

    def _perform_import(self):
        if not self.file_path:
            QMessageBox.warning(
                self, "No file", "Please select an Excel (.xlsx) file to import."
            )
            return
        editor = self.editor_input.text().strip() or "Import"
        try:
            imported_count, messages = import_items_from_excel(
                self.file_path, editor_name=editor
            )
            # Show messages in output
            self.output.clear()
            for m in messages:
                self.output.append(m)

            QMessageBox.information(
                self,
                "Import finished",
                f"Imported {imported_count} rows. See log below for details.",
            )
            self.import_result = (imported_count, messages)
            logger.info(
                f"Import dialog: imported {imported_count} rows from {self.file_path}"
            )
            self.accept()
        except ValueError as ve:
            QMessageBox.critical(self, "Import failed", str(ve))
            self.output.append(str(ve))
        except Exception as e:
            logger.error(f"Unexpected import error: {e}")
            QMessageBox.critical(self, "Import failed", f"Unexpected error: {str(e)}")
            self.output.append(f"Unexpected error: {str(e)}")
