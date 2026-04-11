"""Modal dialog for viewing per-item usage history."""

from datetime import date
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import QDate, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QDateEdit,
    QSpinBox,
    QLineEdit,
    QInputDialog,
    QMessageBox,
)

from inventory_app.utils.logger import logger


class ItemHistoryDialog(QDialog):
    """Shows requisition usage and defective return events for a selected item."""

    defective_data_changed = pyqtSignal()

    COLUMNS = [
        "Event",
        "Activity Date",
        "Quantity",
        "Requested By",
        "Grade",
        "Section",
        "Lab Activity",
        "Request Date",
        "Return Date",
        "Notes",
    ]

    def __init__(
        self,
        item_id: int,
        item_name: str,
        controller,
        initial_event_filter: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.item_id = item_id
        self.item_name = item_name
        self.controller = controller
        self.initial_event_filter = (initial_event_filter or "").strip().lower()
        self._visible_rows: List[Dict[str, Any]] = []
        self._all_rows: List[Dict[str, Any]] = []

        self.setWindowTitle(f"Usage History - {item_name}")
        self.resize(1100, 600)

        self._setup_ui()
        self._load_history()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel(f"Item Usage History: {self.item_name}")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        filter_row = QHBoxLayout()
        self.use_date_range = QCheckBox("Use Activity Date Range")
        self.use_date_range.toggled.connect(self._on_toggle_date_range)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("MM/dd/yyyy")
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setEnabled(False)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("MM/dd/yyyy")
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setEnabled(False)

        self.apply_filters_button = QPushButton("Apply Date Range")
        self.apply_filters_button.setEnabled(False)
        self.apply_filters_button.clicked.connect(self._load_history)

        self.reset_filters_button = QPushButton("All Time")
        self.reset_filters_button.clicked.connect(self._reset_filters)

        self.show_defective_only = QCheckBox("Show Defective Events Only")
        self.show_defective_only.toggled.connect(self._apply_table_filters)
        default_defective_only = self.initial_event_filter == "defective"

        filter_row.addWidget(self.use_date_range)
        filter_row.addWidget(QLabel("From:"))
        filter_row.addWidget(self.date_from)
        filter_row.addWidget(QLabel("To:"))
        filter_row.addWidget(self.date_to)
        filter_row.addWidget(self.apply_filters_button)
        filter_row.addWidget(self.reset_filters_button)
        filter_row.addWidget(self.show_defective_only)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.summary_label = QLabel("")
        layout.addWidget(self.summary_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._update_defective_action_state)
        layout.addWidget(self.table)

        self.defective_actions_row = QHBoxLayout()
        self.defective_actions_label = QLabel(
            "Select a Defective row to confirm as Disposed or Not Defective:"
        )
        self.defective_actions_qty_label = QLabel("Qty:")
        self.defective_actions_qty = QSpinBox()
        self.defective_actions_qty.setRange(1, 1)
        self.defective_actions_qty.setEnabled(False)
        self.defective_actions_notes = QLineEdit()
        self.defective_actions_notes.setPlaceholderText(
            "Optional note for this confirmation"
        )
        self.defective_actions_notes.setEnabled(False)
        self.mark_disposed_button = QPushButton("Confirm Disposed")
        self.mark_not_defective_button = QPushButton("Mark Not Defective")
        self.mark_disposed_button.setEnabled(False)
        self.mark_not_defective_button.setEnabled(False)
        self.mark_disposed_button.clicked.connect(
            lambda: self._apply_defective_confirmation("DISPOSED")
        )
        self.mark_not_defective_button.clicked.connect(
            lambda: self._apply_defective_confirmation("NOT_DEFECTIVE")
        )

        self.defective_actions_row.addWidget(self.defective_actions_label)
        self.defective_actions_row.addWidget(self.defective_actions_qty_label)
        self.defective_actions_row.addWidget(self.defective_actions_qty)
        self.defective_actions_row.addWidget(self.defective_actions_notes, 1)
        self.defective_actions_row.addWidget(self.mark_not_defective_button)
        self.defective_actions_row.addWidget(self.mark_disposed_button)
        layout.addLayout(self.defective_actions_row)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)

        if default_defective_only:
            self.show_defective_only.setChecked(True)

    def _on_toggle_date_range(self, checked: bool) -> None:
        self.date_from.setEnabled(checked)
        self.date_to.setEnabled(checked)
        self.apply_filters_button.setEnabled(checked)
        if not checked:
            self._load_history()

    def _reset_filters(self) -> None:
        self.use_date_range.setChecked(False)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        self._load_history()

    def _load_history(self) -> None:
        start_date: Optional[date] = None
        end_date: Optional[date] = None
        if self.use_date_range.isChecked():
            start_date = self.date_from.date().toPyDate()
            end_date = self.date_to.date().toPyDate()

        rows = self.controller.get_item_usage_history(
            item_id=self.item_id,
            start_date=start_date,
            end_date=end_date,
        )
        self._all_rows = rows
        self._apply_table_filters()

    def _apply_table_filters(self) -> None:
        """Apply local event-type filters on currently loaded rows."""
        if not hasattr(self, "table"):
            return

        rows = self._all_rows
        if self.show_defective_only.isChecked():
            rows = [
                row
                for row in rows
                if (row.get("event_type") or "").strip().lower() == "defective"
            ]
        self._populate_rows(rows)

    def _populate_rows(self, rows: List[Dict[str, Any]]) -> None:
        self._visible_rows = rows

        self.table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            values = [
                row.get("event_type") or "",
                row.get("event_date") or "",
                str(row.get("quantity") or ""),
                row.get("requester_name") or "",
                row.get("grade_level") or "",
                row.get("section") or "",
                row.get("lab_activity") or "",
                row.get("request_date") or "",
                row.get("return_date") or "",
                self._build_notes_cell(row),
            ]

            for col, value in enumerate(values):
                self.table.setItem(row_index, col, QTableWidgetItem(value))

        self.table.resizeColumnsToContents()

        if not rows:
            if self.show_defective_only.isChecked():
                self.summary_label.setText(
                    "No defective history found for this item in the selected range."
                )
            else:
                self.summary_label.setText(
                    "No usage history found for this item in the selected range."
                )
        else:
            if self.show_defective_only.isChecked():
                self.summary_label.setText(
                    f"{len(rows)} defective history events found."
                )
            else:
                self.summary_label.setText(f"{len(rows)} history events found.")

        logger.debug(
            "Loaded %s usage-history rows for item %s",
            len(rows),
            self.item_id,
        )
        self._update_defective_action_state()

    def _build_notes_cell(self, row: Dict[str, Any]) -> str:
        """Compose notes cell text with actionable defective state details."""
        notes = (row.get("notes") or "").strip()
        event_type = (row.get("event_type") or "").strip().lower()
        if event_type != "defective":
            return notes

        pending_qty = int(row.get("pending_defective_qty") or 0)
        disposed_qty = int(row.get("disposed_qty") or 0)
        not_defective_qty = int(row.get("not_defective_qty") or 0)
        state = (
            f"Pending: {pending_qty}, Disposed: {disposed_qty}, "
            f"Not Defective: {not_defective_qty}"
        )
        if notes:
            return f"{notes} | {state}"
        return state

    def _update_defective_action_state(self) -> None:
        """Enable defective action controls when a pending defective row is selected."""
        row_index = self.table.currentRow()
        if row_index < 0 or row_index >= len(self._visible_rows):
            self.defective_actions_qty.setEnabled(False)
            self.defective_actions_notes.setEnabled(False)
            self.mark_disposed_button.setEnabled(False)
            self.mark_not_defective_button.setEnabled(False)
            self.defective_actions_label.setText(
                "Select a Defective row to confirm as Disposed or Not Defective:"
            )
            return

        selected = self._visible_rows[row_index]
        event_type = (selected.get("event_type") or "").strip().lower()
        pending_qty = int(selected.get("pending_defective_qty") or 0)
        has_defective_id = selected.get("defective_item_id") is not None

        is_actionable = (
            event_type == "defective" and has_defective_id and pending_qty > 0
        )
        self.defective_actions_qty.setEnabled(is_actionable)
        self.defective_actions_notes.setEnabled(is_actionable)
        self.mark_disposed_button.setEnabled(is_actionable)
        self.mark_not_defective_button.setEnabled(is_actionable)

        if is_actionable:
            self.defective_actions_qty.setRange(1, pending_qty)
            self.defective_actions_qty.setValue(1)
            self.defective_actions_label.setText(
                f"Selected Defective row pending quantity: {pending_qty}"
            )
        else:
            self.defective_actions_label.setText(
                "Selected row is not actionable. Pick a Defective row with pending quantity."
            )

    def _apply_defective_confirmation(self, action_type: str) -> None:
        """Apply disposed/not-defective confirmation for selected defective row."""
        row_index = self.table.currentRow()
        if row_index < 0 or row_index >= len(self._visible_rows):
            return

        selected = self._visible_rows[row_index]
        defective_item_id = selected.get("defective_item_id")
        if defective_item_id is None:
            return

        qty = int(self.defective_actions_qty.value())
        note = self.defective_actions_notes.text().strip()
        actor, ok = QInputDialog.getText(
            self,
            "Confirmation Required",
            "Enter your name/initials:",
        )
        if not ok or not actor.strip():
            QMessageBox.warning(self, "Required", "Name/initials are required.")
            return

        applied = self.controller.apply_defective_action(
            defective_item_id=int(defective_item_id),
            action_type=action_type,
            quantity=qty,
            acted_by=actor.strip(),
            notes=note,
        )
        if not applied:
            QMessageBox.warning(
                self,
                "Unable To Apply",
                "Could not apply the selected defective confirmation. Please refresh and try again.",
            )
            return

        self.defective_actions_notes.clear()
        self._load_history()
        self.defective_data_changed.emit()
