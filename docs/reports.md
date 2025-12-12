# Reports

Overview

- Reports support Usage, Inventory, and (future) Requisition analytics. Exports are generated as Excel files using `openpyxl`.

Detailed Implementation

- Main Components:
  - `report_generator` (inventory_app/gui/reports/report_generator.py): The central class responsible for generating Excel-based reports. It determines granularity, fetches data using `ReportQueryBuilder`, and writes Excel files using `openpyxl`.
  - `ReportQueryBuilder` (inventory_app/gui/reports/query_builder.py): Builds optimized SQL queries with dynamic period columns and parameterized placeholders to avoid SQL injection. It uses `date_formatter` to generate period keys and converts them to parameterized SQL ranges.
  - `ReportDateFormatter` (inventory_app/gui/reports/report_utils.py): Provides date utilities used across the report system. It determines smart granularity, generates period keys (including "excess" ranges for partial weeks/months/quarters), and formats period headers for Excel.
  - `ReportWorker` (inventory_app/gui/reports/report_worker.py): A `QThread` worker to perform background report generation without blocking the UI. It emits `progress`, `finished`, and `error` signals consumed by the GUI.
  - `MovementType` enum (inventory_app/services/movement_types.py): Enumerates stock movement types used in some inventory reports (e.g., consumption and disposal). This centralizes values used in inventory SQL.

- Excel export details:
  - Uses `openpyxl.Workbook` to construct reports.
  - Headers are formatted via `_format_excel_headers` and period keys are turned into human-readable labels (daily/weekly/monthly/quarterly/yearly) with `ReportDateFormatter` helpers.
  - Applies basic styling: bold headers, colored header background, cell borders, centered alignment, and automatic column width adjustments.
  - Merged cells are handled defensively to avoid type errors.

How Usage Reports are Generated

- Usage reports are generated in `ReportGenerator.generate_report(start_date, end_date, ...)`.
  - The generator computes the smart granularity via `date_formatter.get_smart_granularity`.
  - It invokes `ReportQueryBuilder.build_dynamic_report_query(...)` which:
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
  - Low Stock Alert — items with computed "Current Stock" less than 10 (HAVING clause).
  - Acquisition History — lists `Item_Batches` `date_received` events in range and supplier info.
  - Calibration Due Report — items with `calibration_date` within the range.
- These inventory queries use `MovementType` values for consistency of stock movement semantics and rely on parameterized `?` placeholders for date bounds and filters where applicable.

Statistics and Requisition Reports

- The GUI exposes tabs for Requisition and Statistics reports, but the generator currently returns "not yet implemented" for those report types. The `ReportWorker` and page code provide the UI and placeholders for future implementations.
- The `ReportGenerator.get_usage_statistics(start_date, end_date)` method uses `ReportStatisticsBuilder` to run smaller statistics queries: total items used, category roll-ups, and top used items. This is used by the UI to quickly show summary information.

Background Processing and UI Integration

- The `ReportsPage` UI uses a `DateRangeSelector`, filters, and other controls in `reports_page.py` plus `ReportWorker` to run the chosen report in a separate thread.
- The `ReportWorker` emits progress updates and handles report generation — the UI listens to `progress`, `finished`, and `error` signals and updates `ReportUIUpdater` (status, recent files list, auto-launch on Windows).
- `ReportConfig` centralizes UI strings, granularity descriptions, and styling for the report UI.

Security and SQL Safety

- `ReportQueryBuilder` uses parameterized placeholders (`?`) for all date and filter values so values are not directly interpolated into SQL.
- Dynamic period column aliases are validated using a regex and then safely quoted (double quotes) before being used as column aliases. The code avoids aliasing with untrusted inputs and avoids direct string formatting of parameters.
- The `MovementType` enum centralizes allowed movement types to prevent using arbitrary strings in SQL.

Limitations & Notes

- Requisition and Statistics exports are currently placeholders — selecting them in the UI displays a "Coming Soon" message or returns a not implemented string from the worker.
- The optimized dynamic query builds one CASE WHEN per period. For very large date ranges and extremely small granularity (e.g., daily over many years), the SQL can be large and slow — the `date_formatter.get_smart_granularity` aims to keep queries performant by automatically selecting a coarser granularity when a wide range is requested.
- The query builder includes logic to add "excess" ranges (partial weeks/months/quarters) to ensure coverage and correctness for dates that don't start on period boundaries.

Testing

- Unit tests exist for the query builder and validate that:
  - Parameter placeholders are used and ordered correctly (see `tests/test_report_query_builder.py`).
  - Invalid period keys are skipped to avoid SQL injection.
  - Period parameter counts match expected pairs for generated period keys.
  - Weekly excess ranges are included in period generation and the parameter lists expand accordingly.

Developer Notes

- The Excel file is written to the current working directory by default with a timestamped filename (`{granularity}_report_{YYYYMMDD_HHMMSS}.xlsx` or for inventory reports, `inventory_{report_type}_{timestamp}.xlsx`).
- The report generator logs via `inventory_app.utils.logger` and raises on critical write failures.
- `openpyxl` is declared in `requirements.txt` and used for workbook creation and styling.

Examples and APIs Referenced in Code

- Query building: `ReportQueryBuilder.build_dynamic_report_query(start, end, granularity, grade_filter, section_filter, include_consumables)` returns `(sql, params)`.
- Generating a usage report: `report_generator.generate_report(start, end, output_path=None, grade_filter='', section_filter='')`.
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

References

- See `inventory_app/gui/reports/report_generator.py` for full implementation and `inventory_app/gui/reports/query_builder.py` for SQL query building.
