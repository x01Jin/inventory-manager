"""
Inventory table widget for displaying inventory items.
Provides table display with sorting, and styling.

Optimized for instant population with progressive styling (Chunk 3 of performance plan):
- Phase 1: Instant Population (0-50ms) - data only, no styling
- Phase 2: Essential Styling (50-200ms) - visible rows, critical status colors only
- Phase 3: Full Styling (200ms-2s, progressively) - remaining rows with all styling
"""

from typing import List, Dict, Any, Optional, Set, Callable
from PyQt6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHBoxLayout,
    QWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QLabel,
    QPushButton,
)
from PyQt6.QtCore import Qt, QTimer, QModelIndex, pyqtSignal
from PyQt6.QtGui import QShowEvent, QPainter, QBrush
from PyQt6.QtGui import QColor
from inventory_app.services.item_status_service import item_status_service
from inventory_app.gui.inventory.row_styling_service import row_styling_service
from inventory_app.gui.styles import ThemeManager
from inventory_app.utils.logger import logger

SORT_ROLE = getattr(Qt.ItemDataRole, "SortRole", int(Qt.ItemDataRole.UserRole) + 1)

STYLING_PHASE_DATA = "data"
STYLING_PHASE_ESSENTIAL = "essential"
STYLING_PHASE_FULL = "full"
STYLING_PHASE_COMPLETE = "complete"

CRITICAL_STYLE_CLASSES = {"row-overdue"}

STYLING_BATCH_SIZE = 50
VISIBLE_ROWS_ESTIMATE = 30


class RowColorDelegate(QStyledItemDelegate):
    """
    Custom delegate that ensures row background colors are painted
    even when stylesheets would otherwise override them.
    """

    def paint(
        self,
        painter: Optional[QPainter],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Paint the cell with custom background color if set."""
        if painter is None:
            return

        bg_color = index.data(Qt.ItemDataRole.BackgroundRole)

        if bg_color is not None and isinstance(bg_color, QColor) and bg_color.isValid():
            painter.save()
            painter.fillRect(option.rect, QBrush(bg_color))
            painter.restore()
            option.backgroundBrush = QBrush(bg_color)

        super().paint(painter, option, index)


class AlertIndicator(QWidget):
    """Widget to display indicators in table cells."""

    def __init__(self, alert_type: str = "", parent=None):
        super().__init__(parent)
        self.alert_type = alert_type
        self.setup_ui()

    def setup_ui(self):
        """Setup the alert indicator UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        layout.addStretch()


class InventoryTable(QTableWidget):
    """Table widget for displaying inventory items with optimized progressive styling."""

    sds_requested = pyqtSignal(int)

    CHEMICAL_CATEGORIES = {"Chemicals-Solid", "Chemicals-Liquid"}

    COLUMNS = [
        "Stock/Available",
        "Name",
        "Size",
        "Brand",
        "Other Specifications",
        "Supplier",
        "Calibration Date",
        "Expiry/Disposal Date",
        "Item Type",
        "Acquisition Date",
        "Last Modified",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()
        self._prefetched_statuses: Optional[Dict[int, Any]] = None

        self._row_color_delegate = RowColorDelegate(self)
        self.setItemDelegate(self._row_color_delegate)

        self._styling_phase: str = STYLING_PHASE_COMPLETE
        self._styling_in_progress: bool = False
        self._styling_timer: Optional[QTimer] = None
        self._styling_batch_start: int = 0
        self._styling_callback: Optional[Callable[[], None]] = None
        self._styled_rows: Set[int] = set()
        self._row_status_cache: Dict[int, Any] = {}

    def setup_table(self):
        """Setup the table structure and styling."""
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        header = self.horizontalHeader()
        if header:
            header.setSortIndicatorShown(False)
            header.setSectionsMovable(False)
            header.setStretchLastSection(True)
            header.sectionClicked.connect(self._on_header_clicked)

            self.setColumnWidth(0, 140)
            self.setColumnWidth(1, 200)
            self.setColumnWidth(2, 80)
            self.setColumnWidth(3, 100)
            self.setColumnWidth(4, 120)
            self.setColumnWidth(5, 120)
            self.setColumnWidth(6, 100)
            self.setColumnWidth(7, 100)
            self.setColumnWidth(8, 80)
            self.setColumnWidth(9, 100)
            self.setColumnWidth(10, 120)

        v_header = self.verticalHeader()
        if v_header:
            v_header.setDefaultSectionSize(22)
            v_header.setVisible(False)

    class SortableTableItem(QTableWidgetItem):
        """QTableWidgetItem subclass that prefers SortRole for comparisons."""

        def __lt__(self, other):
            try:
                my = self.data(SORT_ROLE)
                ot = other.data(SORT_ROLE)
                if my is not None and ot is not None:
                    return my < ot
            except Exception:
                pass
            try:
                return (self.text() or "").lower() < (other.text() or "").lower()
            except Exception:
                return super().__lt__(other)

    def _on_header_clicked(self, section: int) -> None:
        """Handle header clicks with sensible default sort ordering."""
        header = self.horizontalHeader()
        current = header.sortIndicatorSection() if header is not None else -1

        if section == 0 and current != 0:
            self.sortItems(0, Qt.SortOrder.AscendingOrder)
            return

        if section == 1 and current != 1:
            self.sortItems(1, Qt.SortOrder.AscendingOrder)
            return

        if section == 5 and current != 5:
            self.sortItems(5, Qt.SortOrder.AscendingOrder)
            return

        if section in (6, 7, 9, 10) and current != section:
            self.sortItems(section, Qt.SortOrder.AscendingOrder)
            return

    def populate_table(
        self,
        items: List[Dict[str, Any]],
        statuses: Optional[Dict[int, Any]] = None,
        skip_styling: bool = False,
        on_styling_complete: Optional[Callable[[], None]] = None,
    ):
        """Populate the table with inventory items with optional progressive styling."""
        try:
            prev_sorting = self.isSortingEnabled()
            self.setSortingEnabled(False)

            # Remove any existing inline row widgets before rebinding row data.
            self._clear_name_column_widgets()

            self.setRowCount(len(items))
            logger.debug(
                f"Populating table with {len(items)} items (skip_styling={skip_styling})"
            )

            self._prefetched_statuses = statuses or {}
            self._row_status_cache = {}
            self._styled_rows = set()

            for row, item in enumerate(items):
                self.populate_row(row, item, skip_styling=skip_styling)
                if not skip_styling and item.get("total_stock", 0) > 0:
                    item_id = item.get("id")
                    if item_id:
                        self._row_status_cache[row] = (
                            statuses.get(item_id) if statuses else None
                        )

            self._prefetched_statuses = {}

            self._styling_callback = on_styling_complete

            if not skip_styling:
                self._start_progressive_styling()
            else:
                QTimer.singleShot(100, self.resize_columns)

            self.setSortingEnabled(prev_sorting)
            if prev_sorting:
                hdr = self.horizontalHeader()
                if hdr is not None:
                    hdr.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
                    hdr.setSortIndicatorShown(False)
                    self.sortItems(0, Qt.SortOrder.AscendingOrder)

        except Exception as e:
            logger.error(f"Error populating table: {e}")

    def populate_row(self, row: int, item: Dict[str, Any], skip_styling: bool = False):
        """Populate a single row with item data."""
        try:
            existing_name_widget = self.cellWidget(row, 1)
            if existing_name_widget is not None:
                self.removeCellWidget(row, 1)
                existing_name_widget.setParent(None)
                existing_name_widget.deleteLater()

            item_id = item.get("id")
            name = item.get("name", "N/A")
            size = item.get("size", "")
            brand = item.get("brand", "")
            other_specifications = item.get("other_specifications", "")
            supplier_name = item.get("supplier_name", "")
            expiration_date = self.format_date(item.get("expiration_date"))
            calibration_date = self.format_date(item.get("calibration_date"))
            acquisition_date = self.format_date(item.get("acquisition_date"))
            is_consumable = item.get("is_consumable", False)
            item_type_text = item.get("item_type")
            last_modified = self.format_datetime(item.get("last_modified"))

            total_stock = item.get("total_stock", 0)
            available_stock = item.get("available_stock", 0)
            stock_display = f"{total_stock}/{available_stock}"

            item_type = item_type_text or (
                "Consumable" if is_consumable else "Non-consumable"
            )

            item_status = None
            if item_id:
                if self._prefetched_statuses is not None:
                    item_status = self._prefetched_statuses.get(item_id)
                else:
                    item_status = item_status_service.get_item_status(item_id)

            stock_item = self.SortableTableItem(stock_display)
            try:
                stock_item.setData(SORT_ROLE, -int(available_stock))
            except Exception:
                stock_item.setData(SORT_ROLE, 0)
            self.setItem(row, 0, stock_item)

            name_item = self.SortableTableItem(name)
            name_item.setData(SORT_ROLE, (name or "").lower())
            self.setItem(row, 1, name_item)
            if (
                item.get("category_name") in self.CHEMICAL_CATEGORIES
                and item_id is not None
            ):
                # Prevent double-rendering text under the inline SDS widget.
                name_item.setText("")
                has_sds = bool(item.get("has_sds", 0))
                self.setCellWidget(
                    row,
                    1,
                    self._build_sds_name_widget(name, item_id, has_sds),
                )
            self.setItem(row, 2, QTableWidgetItem(size or "N/A"))
            self.setItem(row, 3, QTableWidgetItem(brand or "N/A"))
            self.setItem(row, 4, QTableWidgetItem(other_specifications or "N/A"))
            supplier_item = self.SortableTableItem(supplier_name or "N/A")
            supplier_item.setData(SORT_ROLE, (supplier_name or "").lower())
            self.setItem(row, 5, supplier_item)

            cal_date_item = self.SortableTableItem(calibration_date or "N/A")
            try:
                from datetime import datetime

                cal_src = item.get("calibration_date")
                if cal_src:
                    cal_ts = datetime.fromisoformat(cal_src).timestamp()
                    cal_date_item.setData(SORT_ROLE, -float(cal_ts))
                else:
                    cal_date_item.setData(SORT_ROLE, float("inf"))
            except Exception:
                cal_date_item.setData(SORT_ROLE, float("inf"))
            self.setItem(row, 6, cal_date_item)

            exp_date_item = self.SortableTableItem(expiration_date or "N/A")
            try:
                from datetime import datetime

                exp_src = item.get("expiration_date")
                if exp_src:
                    exp_ts = datetime.fromisoformat(exp_src).timestamp()
                    exp_date_item.setData(SORT_ROLE, -float(exp_ts))
                else:
                    exp_date_item.setData(SORT_ROLE, float("inf"))
            except Exception:
                exp_date_item.setData(SORT_ROLE, float("inf"))
            self.setItem(row, 7, exp_date_item)

            self.setItem(row, 8, QTableWidgetItem(item_type))
            acq_item = self.SortableTableItem(acquisition_date)
            try:
                from datetime import datetime

                acq_src = item.get("acquisition_date")
                if acq_src:
                    acq_ts = datetime.fromisoformat(acq_src).timestamp()
                    acq_item.setData(SORT_ROLE, -float(acq_ts))
                else:
                    acq_item.setData(SORT_ROLE, float("inf"))
            except Exception:
                acq_item.setData(SORT_ROLE, float("inf"))
            self.setItem(row, 9, acq_item)

            lm_item = self.SortableTableItem(last_modified)
            try:
                from datetime import datetime

                lm_src = item.get("last_modified")
                if lm_src:
                    lm_ts = datetime.fromisoformat(lm_src).timestamp()
                    lm_item.setData(SORT_ROLE, -float(lm_ts))
                else:
                    lm_item.setData(SORT_ROLE, float("inf"))
            except Exception:
                lm_item.setData(SORT_ROLE, float("inf"))
            self.setItem(row, 10, lm_item)

            if item_id is not None:
                name_item.setData(Qt.ItemDataRole.UserRole, item_id)

            if not skip_styling and total_stock > 0:
                self._apply_row_styling(row, item_status)
                self._styled_rows.add(row)

        except Exception as e:
            logger.error(f"Error populating row {row}: {e}")

    def _start_progressive_styling(self):
        """Start the multi-phase progressive styling process."""
        if self._styling_timer:
            self._styling_timer.stop()
            self._styling_timer = None

        self._styling_phase = STYLING_PHASE_DATA
        self._styling_in_progress = True

        QTimer.singleShot(0, self._apply_essential_styling)

    def _apply_essential_styling(self):
        """Phase 2: Apply styling only to critical items (expired, calibration due)."""
        if self._styling_phase not in (STYLING_PHASE_DATA, STYLING_PHASE_ESSENTIAL):
            return

        self._styling_phase = STYLING_PHASE_ESSENTIAL

        critical_rows = []
        for row in range(self.rowCount()):
            if row in self._styled_rows:
                continue

            status = self._row_status_cache.get(row)
            style_class = row_styling_service.get_row_style_class(status)

            if style_class in CRITICAL_STYLE_CLASSES:
                critical_rows.append(row)
                self._apply_row_styling(row, status)
                self._styled_rows.add(row)

        logger.debug(f"Phase 2 (Essential): Styled {len(critical_rows)} critical rows")

        self._styling_batch_start = 0
        QTimer.singleShot(0, self._apply_full_styling_batch)

    def _apply_full_styling_batch(self):
        """Phase 3: Apply full styling progressively in batches."""
        if self._styling_phase == STYLING_PHASE_COMPLETE:
            return

        self._styling_phase = STYLING_PHASE_FULL

        total_rows = self.rowCount()
        batch_end = min(self._styling_batch_start + STYLING_BATCH_SIZE, total_rows)

        for row in range(self._styling_batch_start, batch_end):
            if row in self._styled_rows:
                self._styling_batch_start += 1
                continue

            status = self._row_status_cache.get(row)
            self._apply_row_styling(row, status)
            self._styled_rows.add(row)
            self._styling_batch_start += 1

        if self._styling_batch_start < total_rows:
            QTimer.singleShot(0, self._apply_full_styling_batch)
        else:
            self._finish_styling()

    def _finish_styling(self):
        """Complete the styling process."""
        self._styling_phase = STYLING_PHASE_COMPLETE
        self._styling_in_progress = False
        self._row_status_cache = {}

        if self._styling_callback:
            self._styling_callback()
            self._styling_callback = None

        logger.debug("Phase 3 (Full): Styling complete")

    def showEvent(self, a0: Optional[QShowEvent]) -> None:
        """Refresh layout and sort indicator on show."""
        super().showEvent(a0)
        QTimer.singleShot(0, self.resize_columns)
        _vp = self.viewport()
        if _vp is not None:
            _vp.update()
        self.repaint()
        header = self.horizontalHeader()
        if header is not None and self.isSortingEnabled():
            sc = header.sortIndicatorSection()
            so = header.sortIndicatorOrder()
            if sc >= 0:
                self.sortItems(sc, so)
                header.setSortIndicatorShown(False)

    def format_date(self, date_str: Optional[str]) -> str:
        """Format date string for display."""
        if not date_str:
            return "N/A"
        try:
            from datetime import datetime

            date_obj = datetime.fromisoformat(date_str)
            return date_obj.strftime("%m/%d/%Y")
        except (ValueError, TypeError):
            return str(date_str)

    def format_datetime(self, datetime_str: Optional[str]) -> str:
        """Format datetime string for display."""
        if not datetime_str:
            return "N/A"
        try:
            from datetime import datetime

            dt_obj = datetime.fromisoformat(datetime_str)
            return dt_obj.strftime("%m/%d/%Y %H:%M")
        except (ValueError, TypeError):
            return str(datetime_str)

    def resize_columns(self):
        """Resize columns to fit content."""
        try:
            for col in range(self.columnCount()):
                self.resizeColumnToContents(col)
                width = self.columnWidth(col)
                self.setColumnWidth(col, max(80, min(width, 200)))
        except Exception as e:
            logger.error(f"Error resizing columns: {e}")

    def get_selected_item_id(self) -> Optional[int]:
        """Get the ID of the currently selected item."""
        current_row = self.currentRow()
        if current_row >= 0:
            item = self.item(current_row, 1)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def clear_table(self):
        """Clear all items from the table."""
        self._clear_name_column_widgets()
        self.setRowCount(0)
        self._styled_rows.clear()
        self._row_status_cache.clear()
        logger.debug("Table cleared")

    def _clear_name_column_widgets(self) -> None:
        """Clear inline widgets from the Name column to prevent stale overlays."""
        for row in range(self.rowCount()):
            widget = self.cellWidget(row, 1)
            if widget is None:
                continue
            self.removeCellWidget(row, 1)
            widget.setParent(None)
            widget.deleteLater()

    def get_row_count(self) -> int:
        """Get the number of rows in the table."""
        return self.rowCount()

    def _build_sds_name_widget(self, name: str, item_id: int, has_sds: bool) -> QWidget:
        """Create a Name + SDS action widget for chemical items."""
        wrapper = QWidget(self.viewport())
        wrapper.setObjectName("sdsInlineWrapper")
        wrapper.setAutoFillBackground(False)
        wrapper.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        wrapper.setStyleSheet("QWidget#sdsInlineWrapper { background: transparent; }")
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        name_label = QLabel(name or "N/A")
        name_label.setObjectName("chemicalNameLabel")
        name_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        name_label.setStyleSheet("background: transparent; border: none;")
        sds_button = QPushButton("SDS")
        sds_button.setObjectName("sdsInlineButton")
        sds_button.setFlat(True)
        sds_button.setStyleSheet(
            "QPushButton#sdsInlineButton {"
            "padding: 0 6px;"
            "margin: 0;"
            "background: transparent;"
            "border: 1px solid rgba(180, 180, 180, 0.45);"
            "border-radius: 7px;"
            "font-size: 9pt;"
            "}"
            "QPushButton#sdsInlineButton:hover {"
            "border: 1px solid rgba(200, 200, 200, 0.75);"
            "}"
        )
        sds_button.setCursor(Qt.CursorShape.PointingHandCursor)
        sds_button.setFixedHeight(18)
        sds_button.setMinimumWidth(36)
        sds_button.clicked.connect(lambda _, iid=item_id: self.sds_requested.emit(iid))

        layout.addWidget(name_label, 1)
        layout.addWidget(sds_button, 0)
        return wrapper

    def _apply_row_styling(self, row: int, item_status) -> None:
        """Apply background color styling to an entire row based on item status."""
        style_class = row_styling_service.get_row_style_class(item_status)

        if not style_class:
            return

        theme_manager = ThemeManager.instance()
        current_theme = theme_manager.current_theme

        bg_color, text_color = row_styling_service.get_row_colors(
            style_class, current_theme
        )

        if bg_color:
            bg_qcolor = QColor(bg_color)
            text_qcolor = QColor(text_color) if text_color else None

            for col in range(self.columnCount()):
                cell_item = self.item(row, col)
                if cell_item:
                    cell_item.setData(Qt.ItemDataRole.BackgroundRole, bg_qcolor)
                    if text_qcolor:
                        cell_item.setData(Qt.ItemDataRole.ForegroundRole, text_qcolor)

    def is_styling_complete(self) -> bool:
        """Check if styling phase is complete."""
        return self._styling_phase == STYLING_PHASE_COMPLETE

    def get_styling_phase(self) -> str:
        """Get current styling phase."""
        return self._styling_phase
