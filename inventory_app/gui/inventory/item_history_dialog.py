"""Modal dialog for viewing per-item usage history."""

from datetime import date
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import QDate
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
)

from inventory_app.utils.logger import logger


class ItemHistoryDialog(QDialog):
    """Shows requisition usage and defective return events for a selected item."""

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
        parent=None,
    ):
        super().__init__(parent)
        self.item_id = item_id
        self.item_name = item_name
        self.controller = controller

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

        filter_row.addWidget(self.use_date_range)
        filter_row.addWidget(QLabel("From:"))
        filter_row.addWidget(self.date_from)
        filter_row.addWidget(QLabel("To:"))
        filter_row.addWidget(self.date_to)
        filter_row.addWidget(self.apply_filters_button)
        filter_row.addWidget(self.reset_filters_button)
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
        layout.addWidget(self.table)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)

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
        self._populate_rows(rows)

    def _populate_rows(self, rows: List[Dict[str, Any]]) -> None:
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
                row.get("notes") or "",
            ]

            for col, value in enumerate(values):
                self.table.setItem(row_index, col, QTableWidgetItem(value))

        self.table.resizeColumnsToContents()

        if not rows:
            self.summary_label.setText(
                "No usage history found for this item in the selected range."
            )
        else:
            self.summary_label.setText(f"{len(rows)} history events found.")

        logger.debug(
            "Loaded %s usage-history rows for item %s",
            len(rows),
            self.item_id,
        )
