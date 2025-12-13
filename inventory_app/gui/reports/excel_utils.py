from typing import List, Dict
from datetime import date
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.cell import MergedCell

from inventory_app.gui.reports.header_utils import format_excel_headers
from inventory_app.utils.logger import logger
from inventory_app.gui.reports.report_utils import date_formatter


def create_excel_report(
    data: List[Dict], output_path: Path, title: str, start_date: date, end_date: date
) -> None:
    """
    Create Excel file with report data.

    Args:
        data: Report data rows
        output_path: Output file path
        title: Report title
        start_date: Report start date
        end_date: Report end date
    """
    try:
        wb = Workbook()
        ws = wb.active
        if ws is None:
            raise ValueError("Could not create worksheet")

        ws.title = "Report"

        # Define styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="366092", end_color="366092", fill_type="solid"
        )
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        center_align = Alignment(horizontal="center")

        # Add title
        ws["A1"] = title
        ws["A1"].font = Font(bold=True, size=16)

        # Use enhanced date formatting for period display
        period_description = date_formatter.get_date_range_description(
            start_date, end_date
        )
        ws["A2"] = f"Period: {period_description}"
        ws["A2"].font = Font(italic=True)

        # Add headers
        numeric_columns = set()
        if data:
            headers = list(data[0].keys())
            formatted_headers = format_excel_headers(headers, start_date, end_date)

            # Detect numeric columns (e.g., quantities, totals, stock)
            for idx, head in enumerate(formatted_headers, 1):
                low = str(head).lower() if head else ""
                if (
                    "quantity" in low
                    or "stock" in low
                    or "total" in low
                    or low.endswith("qty")
                ):
                    numeric_columns.add(idx)

            for col_num, header_text in enumerate(formatted_headers, 1):
                cell = ws.cell(row=4, column=col_num)

                if not isinstance(cell, MergedCell):
                    cell.value = header_text
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = center_align
                    cell.border = border

                # Auto-adjust column width (slightly wider to accommodate sort drop-down)
                column_letter = get_column_letter(col_num)
                # increase header padding to prevent sort/filter button overlap
                ws.column_dimensions[column_letter].width = max(
                    len(str(header_text)) + 6, 12
                )

            # Freeze panes so title/headers remain visible
            try:
                ws.freeze_panes = ws["A5"]
            except Exception:
                pass

            # Auto-filter across headers and data
            try:
                last_col_letter = get_column_letter(len(formatted_headers))
                ws.auto_filter.ref = f"A4:{last_col_letter}{4 + len(data)}"
            except Exception:
                pass

        # Add data rows
        for row_num, row_data in enumerate(data, 5):
            for col_num, value in enumerate(row_data.values(), 1):
                try:
                    cell = ws.cell(row=row_num, column=col_num)

                    if not isinstance(cell, MergedCell):
                        cell.value = value
                        cell.border = border
                        # Apply numeric formatting if this column is numeric
                        if col_num in numeric_columns:
                            try:
                                cell.number_format = "#,##0"
                                cell.alignment = Alignment(horizontal="right")
                            except Exception:
                                pass

                    # Auto-adjust column width based on content - never reduce width
                    column_letter = get_column_letter(col_num)
                    content_length = len(str(value)) + 2
                    current_width = ws.column_dimensions[column_letter].width or 12
                    ws.column_dimensions[column_letter].width = max(
                        current_width, content_length
                    )
                except Exception as e:
                    logger.debug(
                        f"Skipping cell at row {row_num}, column {col_num}: {e}"
                    )

        # Save the workbook
        wb.save(output_path)
        logger.debug(f"Excel file saved to {output_path}")

    except Exception as e:
        logger.error(f"Failed to create Excel report: {e}")
        raise
