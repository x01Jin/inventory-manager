"""Shared helpers for content-aware QTableWidget column sizing."""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

from PyQt6.QtWidgets import QTableWidget


def autosize_table_columns(
    table: QTableWidget,
    width_limits: Optional[Dict[int, Tuple[int, int]]] = None,
    skip_columns: Optional[Iterable[int]] = None,
    minimum_default: int = 80,
    maximum_default: int = 300,
) -> None:
    """Resize QTableWidget columns to contents with per-column bounds.

    Args:
        table: Target table widget.
        width_limits: Optional map of column index -> (min_width, max_width).
        skip_columns: Optional columns to skip from auto-resize.
        minimum_default: Default minimum width for columns not in width_limits.
        maximum_default: Default maximum width for columns not in width_limits.
    """
    limits = width_limits or {}
    skipped = set(skip_columns or [])

    for column in range(table.columnCount()):
        if column in skipped:
            continue

        table.resizeColumnToContents(column)
        current_width = table.columnWidth(column)
        min_width, max_width = limits.get(column, (minimum_default, maximum_default))
        bounded_width = max(min_width, min(current_width, max_width))
        table.setColumnWidth(column, bounded_width)
