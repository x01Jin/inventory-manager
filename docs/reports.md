# Reports

Overview

- Reports support Usage and Inventory analytics. Exports are generated as Excel files using `openpyxl`.

Detailed Implementation

- Main Components:
  - `report_generator` (inventory_app/gui/reports/report_generator.py): The central class responsible for generating Excel-based reports. It determines granularity, fetches data using `ReportQueryBuilder`, and writes Excel files using `openpyxl`.
  - `ReportQueryBuilder` (inventory_app/gui/reports/query_builder.py): Builds optimized SQL queries with dynamic period columns and parameterized placeholders to avoid SQL injection. It uses `date_formatter` to generate period keys and converts them to parameterized SQL ranges.
  - `ReportDateFormatter` (inventory_app/gui/reports/report_utils.py): Provides date utilities used across the report system. It determines smart granularity, generates period keys (including "excess" ranges for partial weeks/months/quarters), and formats period headers for Excel.
  - `ReportWorker` (inventory_app/gui/reports/report_worker.py): A `QThread` worker to perform background report generation without blocking the UI. It emits `progress`, `finished`, and `error` signals consumed by the GUI.
  - `MovementType` enum (inventory_app/services/movement_types.py): Enumerates stock movement types used in some inventory reports (e.g., consumption and disposal). This centralizes values used in inventory SQL.
  - `data_sources` (inventory_app/gui/reports/data_sources.py): Programmatic data retrieval and pivoting. Primary functions:
    - `get_dynamic_report_data(start_date, end_date, granularity, category_filter='', supplier_filter='', include_consumables=True) -> List[Dict]`
    - `get_stock_levels_data(category_filter='') -> List[Dict]`
    - `get_trends_data(start_date, end_date, granularity='monthly', group_by='item', top_n=None, include_consumables=True, category_filter='') -> List[Dict]`
    - `get_expiration_data(start_date, end_date, category_filter='') -> List[Dict]`
    - `get_low_stock_data(category_filter='', threshold=10) -> List[Dict]`
    - `get_acquisition_history_data(start_date, end_date, category_filter='') -> List[Dict]`
    - `get_calibration_due_data(start_date, end_date, category_filter='') -> List[Dict]`
  - `header_utils` (inventory_app/gui/reports/header_utils.py): Header normalization and period key parsing:
    - `format_excel_headers(headers, start_date, end_date) -> List[str]`
    - `parse_and_format_period_key(period_key, granularity) -> str`
  - `excel_utils` (inventory_app/gui/reports/excel_utils.py): Excel file creation and styling:
    - `create_excel_report(data, output_path, title, start_date, end_date) -> None` — writes the workbook, applies header styling, numeric formatting, autofilter, frozen header pane, and increases header column padding to prevent sort/filter control overlap.

- Excel export details:
  - Uses `openpyxl.Workbook` to construct reports.
  - Headers are formatted via `_format_excel_headers` and period keys are turned into human-readable labels (daily/weekly/monthly/quarterly/yearly) with `ReportDateFormatter` helpers.
  - Applies basic styling: bold headers, colored header background, cell borders, centered alignment, and automatic column width adjustments.
  - UX: freeze header panes (`A5` so title and header remain visible), auto-filter enabled on header row for quick data filtering, and numeric formatting for quantity/stock/total columns with right-alignment and thousands grouping where applicable.
  - Merged cells are handled defensively to avoid type errors.
  - Column sizing detail: header columns receive extra padding (approximately +6 characters) to avoid the sort/filter drop-down obscuring header text in generated Excel files.

How Usage Reports are Generated

- Usage reports are generated in `ReportGenerator.generate_report(start_date, end_date, ...)`.
  - The generator computes the smart granularity via `date_formatter.get_smart_granularity`.
  - It invokes `ReportQueryBuilder.build_dynamic_report_query(...)` which:
    - It invokes `ReportQueryBuilder.build_dynamic_report_query(...)` which:
    - Generates period keys (daily/weekly/monthly/quarterly/yearly) with `date_formatter.get_period_keys()` — including "excess" ranges when the date range partially covers a period.
      - Generates period keys (daily/weekly/monthly/quarterly/yearly) with `date_formatter.get_period_keys()` — including "excess" ranges when the date range partially covers a period.
    - Produces a dynamic SQL select with a CASE/WHEN aggregated column for each period key, using parameter placeholders (`?`) for the start and exclusive end of each period column.
    - Validates period key strings used as column aliases with a conservative regex to block malicious alias values.
    - Adds global, half-open WHERE bounds for `r.expected_request >= ? AND r.expected_request < ?` (where the end bound is `end_date + 1 day`).
  - Query parameters ordering: period column bounds first (pairs of [start, end] per period), then global date bounds and filter values.
  - `ReportQueryBuilder.execute_report_query(query, params)` runs the query via the DB connection and returns rows.

Inventory Reports

- Inventory reports are generated via `ReportGenerator.generate_inventory_report(report_type, start_date, end_date, ...)`.
- Implemented inventory report types (UI and code):
  - Stock Levels Report — aggregates `Item_Batches` receipts minus `Stock_Movements` consumption/disposal to compute current stock.
  - Expiration Report — items with `expiration_date` within the given range.
  - Low Stock Alert — items with computed "Current Stock" less than the configured threshold (default 10). Implemented by reusing the Stock Levels query and applying a Python-filtering step to avoid duplicating SQL.
  - Acquisition History — lists `Item_Batches` `date_received` events in range and supplier info.
  - Calibration Due Report — items with `calibration_date` within the range.
- These inventory queries use `MovementType` values for consistency of stock movement semantics and rely on parameterized `?` placeholders for date bounds and filters where applicable.

Background Processing and UI Integration

- The `ReportsPage` UI uses a `DateRangeSelector`, filters, and other controls in `reports_page.py` plus `ReportWorker` to run the chosen report in a separate thread.
- The `ReportWorker` emits progress updates and handles report generation — the UI listens to `progress`, `finished`, and `error` signals and updates `ReportUIUpdater` (status, recent files list, auto-launch on Windows).
- `ReportConfig` centralizes UI strings, granularity descriptions, and styling for the report UI.

Security and SQL Safety

- `ReportQueryBuilder` uses parameterized placeholders (`?`) for all date and filter values so values are not directly interpolated into SQL.
- Dynamic period column aliases are validated using a regex and then safely quoted (double quotes) before being used as column aliases. The code avoids aliasing with untrusted inputs and avoids direct string formatting of parameters.
- The `MovementType` enum centralizes allowed movement types to prevent using arbitrary strings in SQL.

Limitations & Notes

- Usage statistics are still available programmatically via `ReportGenerator.get_usage_statistics(start_date, end_date)`.
- The optimized dynamic query builds one CASE WHEN per period. For very large date ranges and extremely small granularity (e.g., daily over many years), the SQL can be large and slow — the `date_formatter.get_smart_granularity` aims to keep queries performant by automatically selecting a coarser granularity when a wide range is requested.
- The query builder includes logic to add "excess" ranges (partial weeks/months/quarters) to ensure coverage and correctness for dates that don't start on period boundaries.

Testing

- Unit tests exist for the query builder and validate that:
  - Parameter placeholders are used and ordered correctly (see `tests/test_report_query_builder.py`).
  - Invalid period keys are skipped to avoid SQL injection.
  - Period parameter counts match expected pairs for generated period keys.
  - Weekly excess ranges are included in period generation and the parameter lists expand accordingly.
  - Header normalization tests exist (see `tests/test_report_headers.py`) and validate that header mapping (`REPORT_HEADER_MAP`) and period header parsing produce expected Title Case and formatted header labels.

Developer Notes

- The Excel file is written to the current working directory by default with a timestamped filename (`{granularity}_report_{YYYYMMDD_HHMMSS}.xlsx` or for inventory reports, `inventory_{report_type}_{timestamp}.xlsx`).
- The report generator logs via `inventory_app.utils.logger` and raises on critical write failures.
- `openpyxl` is declared in `requirements.txt` and used for workbook creation and styling.

Examples and APIs Referenced in Code

- Query building: `ReportQueryBuilder.build_dynamic_report_query(start, end, granularity, category_filter, supplier_filter, include_consumables)` returns `(sql, params)`.
- Headers: Excel headers are normalized via `REPORT_HEADER_MAP` (e.g., `ITEMS`/`Item Name` -> `Item`, `TOTAL QUANTITY` -> `Total Quantity`).
- Headers: Excel headers are normalized via `header_utils.format_excel_headers` (maps canonical names and formats period keys into human-friendly labels).
- Excel creation: Use `excel_utils.create_excel_report(data, output_path, title, start_date, end_date)` to write styled workbooks programmatically.
- Data retrieval: Use `data_sources.get_dynamic_report_data(...)` for pivoted time-series rows when building reports programmatically.
- Generating a usage report: `report_generator.generate_report(start, end, output_path=None, category_filter='', supplier_filter='')`.
- Generating an inventory report: `report_generator.generate_inventory_report(report_type, start_date, end_date, category_filter='', output_path=None)`.
- Getting usage statistics: `report_generator.get_usage_statistics(start_date, end_date)`.

Contributing & Future Work

- Add Requisition and Statistics report implementations in `ReportGenerator` and corresponding query builders.
- Add streaming or pagination export for very large data sets to avoid memory pressure when building workbooks.
- Add caching for repeated report queries for repeated runs with identical parameters.
- Consider optimizing the dynamic SQL approach for extremely large ranges (e.g., grouping into fewer columns or post-processing aggregates).

Common Reports

- Stock Levels
- Expiration
- Low Stock Alerts
- Acquisition History
- Calibration Due
- Trends (grouping by item or category; time-series heatmap/top-N)

References

- See `inventory_app/gui/reports/report_generator.py` for full implementation and `inventory_app/gui/reports/query_builder.py` for SQL query building.
