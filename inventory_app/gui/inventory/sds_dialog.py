"""Dialog for viewing and managing item SDS records."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
)

from inventory_app.database.models import ItemSDS
from inventory_app.services.sds_storage_service import sds_storage_service
from inventory_app.utils.logger import logger


class SDSDialog(QDialog):
    """Dialog for SDS upload/update/remove actions with audit attribution."""

    def __init__(self, item_id: int, item_name: str = "", parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.item_name = item_name
        self.current_sds: Optional[ItemSDS] = None
        self.pending_source_path: Optional[str] = None

        self.setWindowTitle("Safety Data Sheet")
        self.resize(680, 420)
        self._setup_ui()
        self._load_existing_sds()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(f"Item: {self.item_name or self.item_id}")
        layout.addWidget(title)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("SDS File:"))
        self.file_path_input = QLineEdit()
        self.file_path_input.setReadOnly(True)
        self.file_path_input.setPlaceholderText("No SDS file uploaded")
        file_row.addWidget(self.file_path_input)
        layout.addLayout(file_row)

        notes_label = QLabel("SDS Notes:")
        layout.addWidget(notes_label)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText(
            "Optional notes (e.g., hazard class, first aid summary, handling guidance)."
        )
        layout.addWidget(self.notes_input, 1)

        editor_row = QHBoxLayout()
        editor_row.addWidget(QLabel("Editor Name/Initials (required):"))
        self.editor_input = QLineEdit()
        self.editor_input.setPlaceholderText("Enter your name or initials")
        editor_row.addWidget(self.editor_input)
        layout.addLayout(editor_row)

        actions_row = QHBoxLayout()
        self.upload_btn = QPushButton("Upload/Replace File")
        self.upload_btn.clicked.connect(self._pick_file)
        actions_row.addWidget(self.upload_btn)

        self.open_btn = QPushButton("Open File")
        self.open_btn.clicked.connect(self._open_file)
        actions_row.addWidget(self.open_btn)

        self.remove_btn = QPushButton("Remove SDS")
        self.remove_btn.clicked.connect(self._remove_sds)
        actions_row.addWidget(self.remove_btn)

        actions_row.addStretch()
        layout.addLayout(actions_row)

        footer = QHBoxLayout()
        footer.addStretch()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save)
        footer.addWidget(self.save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)
        layout.addLayout(footer)

    def _load_existing_sds(self) -> None:
        self.current_sds = ItemSDS.get_by_item_id(self.item_id)
        if not self.current_sds:
            self.file_path_input.setText("")
            self.open_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
            return

        self.file_path_input.setText(self.current_sds.file_path or "")
        self.notes_input.setPlainText(self.current_sds.sds_notes or "")
        has_file = bool(self.current_sds.file_path)
        self.open_btn.setEnabled(has_file)
        self.remove_btn.setEnabled(True)

    def _pick_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SDS File",
            "",
            "Documents (*.pdf *.doc *.docx *.txt *.png *.jpg *.jpeg);;All Files (*.*)",
        )
        if not file_path:
            return

        self.pending_source_path = file_path
        self.file_path_input.setText(file_path)
        self.open_btn.setEnabled(True)

    def _open_file(self) -> None:
        target_path = self.pending_source_path or self.file_path_input.text().strip()
        if not target_path:
            QMessageBox.information(self, "SDS", "No SDS file selected.")
            return

        local_path = Path(target_path)
        if not local_path.exists():
            QMessageBox.warning(
                self, "Missing File", "The SDS file could not be found."
            )
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(local_path.resolve())))

    def _remove_sds(self) -> None:
        editor_name = self.editor_input.text().strip()
        if not editor_name:
            QMessageBox.warning(self, "Validation Error", "Editor name is required.")
            return

        if not self.current_sds:
            QMessageBox.information(self, "SDS", "No SDS record exists for this item.")
            return

        confirm = QMessageBox.question(
            self,
            "Remove SDS",
            "Remove SDS metadata and file for this item?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        file_removed = sds_storage_service.remove_file(self.current_sds.file_path)
        if not file_removed:
            QMessageBox.warning(
                self,
                "Warning",
                "SDS metadata can still be removed, but file deletion failed.",
            )

        success = ItemSDS.delete_for_item(
            self.item_id,
            editor_name,
            reason="SDS removed",
        )
        if not success:
            QMessageBox.critical(self, "Error", "Failed to remove SDS record.")
            return

        QMessageBox.information(self, "Success", "SDS removed successfully.")
        self.accept()

    def _save(self) -> None:
        editor_name = self.editor_input.text().strip()
        if not editor_name:
            QMessageBox.warning(self, "Validation Error", "Editor name is required.")
            return

        sds_notes = self.notes_input.toPlainText().strip() or None
        existing = self.current_sds
        has_existing_file = bool(existing and existing.file_path)

        if not self.pending_source_path and not has_existing_file and not sds_notes:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Upload an SDS file or provide SDS notes before saving.",
            )
            return

        old_path: Optional[str] = existing.file_path if existing else None
        copied_path: Optional[str] = None

        sds = existing or ItemSDS(item_id=self.item_id)

        if self.pending_source_path:
            metadata = sds_storage_service.store_file(
                self.item_id, self.pending_source_path
            )
            if not metadata:
                QMessageBox.critical(self, "Error", "Failed to store SDS file.")
                return

            copied_path = metadata["file_path"]
            sds.stored_filename = metadata["stored_filename"]
            sds.original_filename = metadata["original_filename"]
            sds.file_path = metadata["file_path"]
            sds.mime_type = metadata["mime_type"]

        sds.sds_notes = sds_notes
        reason = "SDS uploaded" if existing is None else "SDS updated"

        if not sds.save(editor_name, reason=reason):
            if copied_path:
                sds_storage_service.remove_file(copied_path)
            QMessageBox.critical(self, "Error", "Failed to save SDS metadata.")
            return

        if self.pending_source_path and old_path and old_path != sds.file_path:
            sds_storage_service.remove_file(old_path)

        logger.info(f"SDS saved for item {self.item_id} by {editor_name}")
        QMessageBox.information(self, "Success", "SDS saved successfully.")
        self.accept()
