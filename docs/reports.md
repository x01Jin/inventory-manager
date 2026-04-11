# Reports

## Overview

- Reports support Usage, Inventory, Trends, and Audit analytics. Exports are generated as Excel files using `openpyxl`.
- **Usage counting is based on lab_activity_date** (when materials are actually used in lab activities), NOT the borrow/request date.

## Usage Reports

The Usage Reports tab provides two distinct report types accessible through a dropdown selector:

### Monthly Usage Report

Generates a detailed monthly report in the format specified in beta test requirements #20, #21:

- **Format**: Excel file with category-grouped items and weekly breakdown
- **Data Filtering**: Only items with actual usage during the month are included (items with zero usage are excluded from the report)
- **Layout**:
  - Row 1: Empty (spacing)
  - Row 2: Title header merged in columns F-G ("REPORT ON THE USAGE OF LABORATORY MATERIALS, EQUIPMENT AND APPRATUSES, ETC. FOR THE MONTH OF [MONTH]")
  - Row 3: Empty (spacing)
  - Row 4: Base column headers (ITEMS, CATEGORIES, ACTUAL INVENTORY, SIZE, BRAND, OTHER SPECIFICATIONS) + Month name centered over week columns + "Total Number of" header
  - Row 5: Week labels (PRE, WEEK 1, WEEK 2, WEEK 3, WEEK 4, POST) + "Usage per Item" header
  - Row 6: Date range labels under each week (e.g., "Oct 3-7", "Oct 10-14")
  - Row 7+: Data rows grouped by category with category header rows

- **Week Structure (PRE/POST Excess)**:
  - **PRE**: Days from month start to Saturday before first full week (if month doesn't start on Monday)
  - **WEEK 1-4**: Full weeks (Monday-Sunday) within the month
  - **POST**: Days from Monday after last full week to month end (if month doesn't end on Sunday)

- **Example for October 2025**:
  - PRE: Oct 1-5 (Wednesday-Sunday before first Monday)
  - WEEK 1: Oct 6-12
  - WEEK 2: Oct 13-19
  - WEEK 3: Oct 20-26
  - POST: Oct 27-31 (Monday-Friday after last full week)

- **Columns**:
  - **ITEMS**: Item name (equipment, apparatus, etc.)
  - **CATEGORIES**: Category name (Apparatus, Equipment, Chemicals, etc.)
  - **ACTUAL INVENTORY**: Current stock quantity from Item_Batches
  - **SIZE**: Item size specification
  - **BRAND**: Item brand
  - **OTHER SPECIFICATIONS**: Additional specifications (wood, metal, glass, etc.)
  - **PRE/WEEK 1-4/POST**: Usage count for each period based on lab_activity_date
  - **Total Number of Usage per Item**: Sum of all weekly usage

- **Category Grouping**: Items grouped by category with gold-colored header rows:
  - APPARATUSES
  - EQUIPMENT
  - LAB MODELS
  - CHEMICALS - SOLID
  - CHEMICALS - LIQUID
  - PREPARED SLIDES
  - CONSUMABLES
  - OTHERS

- **Configuration**:
  - Year and month selection via spinbox and dropdown
  - Category filter (All Categories or specific)
  - Report style: Detailed (Full Title) or Simple (Short Title)

### Date Range Usage Report

Generates a time-series usage report for any custom date range with automatic granularity selection:

- **Format**: Excel file with dynamic period columns and time-series analysis
- **Granularity**: Automatically selected based on date range (Daily, Weekly, Monthly, Yearly) via `ReportDateFormatter.get_smart_granularity`
- **Features**:
  - Dynamic period columns with CASE/WHEN aggregation for each period
  - Period keys include "excess" ranges for partial weeks/months
  - Parameterized SQL queries to prevent injection
  - Filterable by category
  - Optional consumable item inclusion
  - Preset date ranges for quick selection (Last 7/30/90 Days, This/Last Month, This/Last Year)

- **Configuration**:
  - Custom date range selection via DateRangeSelector
  - Preset date ranges for quick access
  - Category filter (All Categories or specific)
  - **Individual Requests Filter**: "Show only individual requests" checkbox to filter for ad-hoc/unaffiliated requisitions
  - Consumable items checkbox (enabled by default)

## Detailed Implementation

- Main Components:
  - `ReportsPage` (inventory_app/gui/reports/reports_page.py): The main UI page with merged Usage Reports tab providing both monthly and date range report types via a dropdown selector. Each report type maintains its own separate UI.
  - `report_generator` (inventory_app/gui/reports/report_generator.py): The central class responsible for generating Excel-based reports. It determines granularity, fetches data using `ReportQueryBuilder`, and writes Excel files using `openpyxl`.
  - `ReportQueryBuilder` (inventory_app/gui/reports/query_builder.py): Builds optimized SQL queries with dynamic period columns and parameterized placeholders to avoid SQL injection. It uses `date_formatter` to generate period keys and converts them to parameterized SQL ranges.
  - `ReportDateFormatter` (inventory_app/gui/reports/report_utils.py): Provides date utilities used across the report system. It determines smart granularity, generates period keys (including "excess" ranges for partial weeks/months), and formats period headers for Excel.
  - `ReportWorker` (inventory_app/gui/reports/report_worker.py): A `QThread` worker to perform background report generation without blocking the UI. It emits `progress`, `finished`, and `error` signals consumed by the GUI.
  - `MovementType` enum (inventory_app/services/movement_types.py): Enumerates stock movement types used in some inventory reports (e.g., consumption and disposal). This centralizes values used in inventory SQL.
  - `data_sources` (inventory_app/gui/reports/data_sources.py): Programmatic data retrieval and pivoting. Primary functions:
    - `get_dynamic_report_data(start_date, end_date, granularity, category_filter='', supplier_filter='', include_consumables=True) -> List[Dict]`
    - `get_stock_levels_data(category_filter='') -> List[Dict]`
    - `get_trends_data(start_date, end_date, granularity=None|'auto', group_by='item', top_n=None, include_consumables=True, category_filter='') -> List[Dict]` — `granularity` defaults to `None` (Auto) and will use the smart granularity computed from the date range when unset.
    - `get_expiration_data(start_date, end_date, category_filter='') -> List[Dict]`
    - `get_calibration_due_data(start_date, end_date, category_filter='') -> List[Dict]`
    - `get_update_history_data(start_date, end_date, item_filter='') -> List[Dict]` — edit history with editor, reason, and field-level old/new values
    - `get_disposal_history_data(start_date, end_date, category_filter='') -> List[Dict]` — disposal records with reason
    - `get_defective_items_data(start_date, end_date, category_filter='') -> List[Dict]` — defective/broken items returned
    - `get_audit_log_data(start_date, end_date, editor_filter='', action_filter='', entity_filter='') -> List[Dict]` — unified Task 9 audit dataset
  - `header_utils` (inventory_app/gui/reports/header_utils.py): Header normalization and period key parsing:
    - `format_excel_headers(headers, start_date, end_date) -> List[str]`
    - `parse_and_format_period_key(period_key, granularity) -> str`
    - Note: `format_excel_headers` is consumed by `excel_utils.create_excel_report` and is used by both Usage/Trends and Inventory exports (when they contain period column keys). It delegates to `parse_and_format_period_key` to convert period keys into human-friendly labels.
  - `excel_utils` (inventory_app/gui/reports/excel_utils.py): Excel file creation and styling:
    - `create_excel_report(data, output_path, title, start_date, end_date, granularity=None) -> None` — writes the workbook, applies header styling, numeric formatting, autofilter, frozen header pane, and increases header column padding to prevent sort/filter control overlap.

- **Zero-Stock Item Filtering**: Items with 0 current stock (fully depleted or disposed) are excluded from:
  - Expiration alerts/reports (items are assumed depleted and no longer relevant for expiration tracking)
  - Calibration alerts/reports (items are assumed disposed and no longer need calibration tracking)
  - Stock level reports (items with 0 stock are filtered out to show only active inventory)
  - Low stock warnings (percentage thresholds skip items with 0 original stock)
  - Dashboard alerts and status indicators
  - Note: Zero-stock items remain in the inventory table and database for historical record keeping and requisition integrity

- Excel export details:
  - Uses `openpyxl.Workbook` to construct reports.
  - Headers are formatted via `_format_excel_headers` and period keys are turned into human-readable labels (daily/weekly/monthly/yearly) with `ReportDateFormatter` helpers.
  - Applies basic styling: bold headers, colored header background, cell borders, centered alignment, and automatic column width adjustments.
  - UX: freeze header panes (`A5` so title and header remain visible), auto-filter enabled on header row for quick data filtering, and numeric formatting for quantity/stock/total columns with right-alignment and thousands grouping where applicable.
  - Merged cells are handled defensively to avoid type errors.
  - Column sizing detail: header columns receive extra padding (approximately +6 characters) to avoid the sort/filter drop-down obscuring header text in generated Excel files.

## How Usage Reports are Generated

### Monthly Usage Report Generation

Monthly reports are generated via `ReportGenerator.generate_monthly_usage_report(year, month, category_filter='', report_style='detailed')`:

- The monthly report generator determines week boundaries using `get_month_weeks()` which calculates PRE/WEEK 1-4/POST periods
- Data is fetched from the database using movement counts grouped by week periods and category
- Items are sorted into category groups with gold-colored header rows
- Excel file is formatted with the multi-row header structure matching beta test requirements
- Category-level subtotals are calculated
- Report style determines title verbosity

### Date Range Usage Report Generation

Date Range reports are generated in `ReportGenerator.generate_report(start_date, end_date, ...)`:

- The generator computes the smart granularity via `date_formatter.get_smart_granularity`.
- It invokes `ReportQueryBuilder.build_dynamic_report_query(...)` which:
  - Generates period keys (daily/weekly/monthly/yearly) with `date_formatter.get_period_keys()` — including "excess" ranges when the date range partially covers a period.
  - Produces a dynamic SQL select with a CASE/WHEN aggregated column for each period key, using parameter placeholders (`?`) for the start and exclusive end of each period column.
  - Validates period key strings used as column aliases with a conservative regex to block malicious alias values.
  - Adds global, half-open WHERE bounds for `r.expected_request >= ? AND r.expected_request < ?` (where the end bound is `end_date + 1 day`).
- Query parameters ordering: period column bounds first (pairs of [start, end] per period), then global date bounds and filter values.
- `ReportQueryBuilder.execute_report_query(query, params)` runs the query via the DB connection and returns rows.

## Inventory Reports

- Inventory reports are generated via `ReportGenerator.generate_inventory_report(report_type, start_date, end_date, ...)`.
- Implemented inventory report types (UI and code):
  - Stock Levels Report:
    - Consumables: `Original - Consumption - Disposal + Return`
    - Non-consumables: `Original - Disposal` (active borrow/request affects availability, not baseline stock)
  - Expiration Report — items with `expiration_date` within the given range. Addresses beta test requirement #10 for expiration alerts.
  - Calibration Due Report — items in calibration-enabled categories with `calibration_date` within the range (default policy: Equipment). Addresses beta test requirement #11 for calibration alerts.
  - Update History Report — history of edits to inventory items with editor name, timestamp, and reason. Addresses beta test requirement #7.
  - Disposal History Report — disposed items with disposal date, reason, and who disposed them. Addresses beta test requirement #16.
  - Defective Items Report — defective/broken items returned with notes, reporter, and date. Addresses beta test requirement B.3.
  - Audit Log Report — centralized audit stream across item/requisition updates, disposals, defective recordings, and activity events.
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
- The query builder includes logic to add "excess" ranges (partial weeks/months) to ensure coverage and correctness for dates that don't start on period boundaries.

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
- Excel creation: Use `excel_utils.create_excel_report(data, output_path, title, start_date, end_date, granularity=None)` to write styled workbooks programmatically.
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
- Calibration Due (calibration-enabled categories only)
- Trends (grouping by item or category; time-series heatmap/top-N). Default granularity is `Auto` (uses the same smart granularity rules as Usage reports); manual granularity selection is still supported.
- **Update History Report** - Shows history of edits to inventory items including editor name, timestamp, and reason
- **Disposal History Report** - Shows disposed items with disposal date, reason, and who disposed them
- **Defective Items Report** - Shows defective/broken items returned with condition type, notes, reporter, and date
- **Audit Log Report** - Shows centralized history across item/requisition edits, disposals, defective recordings, and activity events, including field-level old/new values when available
- Defective return processing now emits a dedicated activity type (`ITEM_MARKED_DEFECTIVE`) so dashboard/activity feeds can distinguish defect recordings from generic return-finalization events
- **Usage by Grade Level Report** - Shows item usage grouped by grade level and section, with optional filter for individual requests only

## Usage by Grade Level Report

The Usage by Grade Level Report tracks item consumption across educational groups:

- **Columns**: Item Name, Category, Grade Level, Section, Quantity Used, Lab Activity, Activity Date
- **Filtering**:
  - By date range
  - By category
  - By grade level (All Grades or specific)
  - By section (All Sections or specific)
  - **Individual Requests Only**: Checkbox to show only ad-hoc/unaffiliated requisitions (grade/section filters disabled when this is checked)
- **Source**: Requisitions with Requesters joined to get grade/section data

## Defective Items Report

The Defective Items Report tracks broken/defective items returned from requisitions:

- **Columns**: Item Name, Category, Size, Brand, Defective Quantity, Notes, Reported By, Report Date, Lab Activity, Requester
- **Filtering**: By date range and category
- **Source**: Defective_Items table populated during return processing

## References

- See `inventory_app/gui/reports/report_generator.py` for full implementation and `inventory_app/gui/reports/query_builder.py` for SQL query building.
- Monthly Usage Report: `inventory_app/gui/reports/monthly_usage_report.py`
