from typing import List, Optional
from datetime import date, timedelta
from inventory_app.utils.logger import logger
from inventory_app.gui.reports.report_utils import date_formatter

REPORT_HEADER_MAP = {
    "ITEMS": "Item",
    "ITEM": "Item",
    "Item Name": "Item",
    "CATEGORIES": "Category",
    "Category": "Category",
    "Original Stock": "Original Stock",
    "ACTUAL_INVENTORY": "Current Stock",
    "Current Stock": "Current Stock",
    "TOTAL QUANTITY": "Total Quantity",
    "Quantity Received": "Quantity Received",
    "OTHER SPECIFICATIONS": "Specifications",
    "OTHER SPEC": "Specifications",
    "Specifications": "Specifications",
    "SIZE": "Size",
    "Size": "Size",
    "BRAND": "Brand",
    "Brand": "Brand",
    "Expiration Date": "Expiration Date",
    "Acquisition Date": "Acquisition Date",
    "Calibration Date": "Calibration Date",
    "Supplier": "Supplier",
}


def format_excel_headers(
    headers: List[str],
    start_date: date,
    end_date: date,
    granularity: Optional[str] = None,
) -> List[str]:
    """
    Format Excel headers by converting period keys to user-friendly format.
    """
    try:
        if granularity is None:
            granularity = date_formatter.get_smart_granularity(start_date, end_date)
        formatted_headers = []

        for header in headers:
            if header in REPORT_HEADER_MAP:
                formatted_headers.append(REPORT_HEADER_MAP[header])
                continue

            try:
                formatted_header = parse_and_format_period_key(header, granularity)
                formatted_headers.append(formatted_header)
            except Exception:
                logger.warning(f"Could not parse period key: {header}")
                formatted_headers.append(header)

        return formatted_headers

    except Exception as e:
        logger.error(f"Failed to format Excel headers: {e}")
        return headers


def parse_and_format_period_key(period_key: str, granularity: str) -> str:
    """
    Parse a period key and format it according to granularity.
    """
    try:
        if "to" in period_key:
            start_date_str, end_date_str = period_key.split("to")
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)

            month_names = [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ]

            start_month = month_names[start_date.month - 1]
            end_month = month_names[end_date.month - 1]

            if start_date.month == end_date.month:
                return f"({start_month}/{start_date.day:02d}-{end_date.day:02d}/{start_date.year})"
            else:
                return f"({start_month}/{start_date.day:02d}-{end_month}/{end_date.day:02d}/{start_date.year})"

        if granularity == "daily":
            parsed_date = date.fromisoformat(period_key)
            return date_formatter.format_period_header(parsed_date, "daily")

        elif granularity == "weekly":
            try:
                year_str, month_str, week_part = period_key.split("-")
                year, month = int(year_str), int(month_str)
                week_str = week_part.replace("W", "")
                week_num = int(week_str)

                first_day_of_month = date(year, month, 1)
                week_date = first_day_of_month + timedelta(days=(week_num - 1) * 7)

                return date_formatter.format_period_header(week_date, "weekly")
            except (ValueError, IndexError):
                return period_key

        elif granularity == "monthly":
            year_str, month_str = period_key.split("-")
            year, month = int(year_str), int(month_str)
            month_date = date(year, month, 1)

            return date_formatter.format_period_header(month_date, "monthly")

        elif granularity in ["yearly", "multi_year"]:
            year = int(period_key)
            year_date = date(year, 1, 1)

            return date_formatter.format_period_header(year_date, "yearly")

        else:
            return period_key

    except Exception as e:
        logger.error(f"Failed to parse period key '{period_key}': {e}")
        return period_key
