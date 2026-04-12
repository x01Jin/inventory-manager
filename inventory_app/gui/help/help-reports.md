# Reports Help

The Reports page is where you generate, inspect, and export detailed, Excel-compatible reports about inventory, usage, and time-based trends. It provides flexible filters and options so you can create the exact dataset you need for auditing, stock management, or sharing with colleagues.

## **Top controls (header)**

- **🔄 Refresh:** Reloads category/filter options and refreshes the generated Excel file list from the reports folder.
- **📅 Date range presets:** Quick presets such as **Last 7 Days**, **Last 30 Days**, **This Month**, **Last Month**, **This Year**, and **Last Year** let you set common ranges in one click.
- **🚀 Generate Report:** Start generation of the currently selected report with the chosen options. Report generation runs in the background and the UI displays progress messages.

## **Report Types & Tabs**

There are four main tabs: **Usage Reports**, **Inventory Reports**, **Trends Reports**, and **Audit Log**. Choose the tab that matches your need, configure options, and click **Generate Report**.

- **Usage Reports:** Time-bucketed usage of items across the selected date range. Use the **Report Type** dropdown to choose between **Monthly Usage** (grouped by week within a month, with category grouping) or **Date Range** (flexible date range with daily/weekly/monthly/yearly granularity). Monthly Usage supports category filtering and is the default selection. The counts reflect actual laboratory activity dates (when materials were used in lab activities), not when they were borrowed.
- **Inventory Reports:** Several prebuilt inventory-focused exports including **Stock Levels Report**, **Expiration Report**, **Low Stock Alert**, **Acquisition History**, **Calibration Due Report**, **Update History Report**, **Disposal History Report**, **Usage by Grade Level**, and **Defective Items Report**. Some reports use date ranges (e.g., Acquisition History, Expiration windows). Others show current or historical state.
- **Trends Reports:** Time-series (pivoted) reports grouped by **Item** or **Category**, with Auto/manual **Granularity** (Daily/Weekly/Monthly/Yearly), and an optional **Top N** filter (Top 10/20/50/All).
- **Audit Log:** Centralized report stream for auditing. It combines item/requisition updates, disposals, defective recordings, SDS lifecycle events, and activity events. Filters include date range, editor name/initials, action type, and entity type.

## **Filters & Options**

- **Date Range:** Use the date selector or quick presets to pick the report window. The UI validates start ≤ end and will warn if the range is invalid.
- **Category / Supplier filters (Usage/Inventory):** Restrict the report to a subset of items.
- **Include consumables:** Toggle whether consumable items are included in Usage/Trends reports.
- **Low Stock Threshold (Inventory → Low Stock Alert):** By default the application uses percentage-based thresholds (Consumables 20% / Non-consumables 10%). You can opt to supply an absolute unit threshold by toggling the percentage-mode checkbox and entering a number.
- **Granularity (Trends):** The system auto-selects a sensible granularity based on the length of the date range. You can override using the Granularity menu. Hover the granularity control for an explanation of how the Auto selection works.
- **Group By / Top N (Trends):** Group by `Item` or `Category` and optionally limit the output to the top N items by usage.

## **What each report contains (at-a-glance)**

- **Monthly Usage Report:** Items grouped by category with weekly breakdown for a selected month. Includes columns: ITEMS, CATEGORIES, ACTUAL INVENTORY, SIZE, BRAND, OTHER SPECIFICATIONS, GRADE 7-10, TOTAL GRADE USAGE, PRE/WEEK 1-4/POST, and Total Usage. ACTUAL INVENTORY follows Task 10 stock policy.
- **Date Range Usage Report:** Period-by-period breakdown of quantity moved/used per item (columns represent time-period buckets determined by granularity). Headers and period labels are formatted for readability (title-case and human-friendly period labels), and report title period text shows exact selected dates (example: `Jan 1, 2026 - Jan 5, 2026`). Includes supplier in base columns and supports category filtering in UI.
- **Stock Levels Report:** Current stock per item (includes total and available quantities where appropriate). Useful for stock-taking and audits:
  - Consumables: `Original - Consumption - Disposal + Return`
  - Non-consumables: `Original - Disposal` (borrow/request affects availability, not baseline stock)
  - Includes supplier names in exported rows.
- **Expiration Report:** Items and batches expiring inside the selected window, with dates and batch details where available.
- **Low Stock Alert:** Items below the configured threshold. When using percentage mode it applies 20%/10% defaults depending on item type.
- **Acquisition History:** Incoming/received batches and quantities during the date range, with batch sequence labels (B1, B2, B3, etc.).
- **Calibration Due Report:** Items in calibration-enabled categories (default: Equipment) with calibration due within the selected window.
- **Update History Report:** Complete history of all edits to inventory items within the date range, including who edited (editor name), when, reason, and field-level old/new values when available.
- **Disposal History Report:** Profile of disposed/deleted items with disposal date, reason, who disposed them, and category grouping.
- **Usage by Grade Level:** Item-level usage breakdown with Grade 7/8/9/10 tally columns plus TOTAL QUANTITY and inventory descriptors (size, brand, specs). Supports date range, category, grade, section, and individual-request filtering.
- **Defective Items Report:** Items reported as defective or damaged during requisition returns, including quantity, notes, and who reported.
- **Audit Log Report:** Unified audit history including item/requisition changes, disposals, defective recordings, SDS upload/removal events, and activity log events.
  - Item/requisition field edits are grouped into a single event row with a readable `Summary` description.
- **Trends Reports:** Pivoted time-series tables where rows are items or categories and columns are period buckets (daily, weekly, monthly, yearly) depending on granularity.

## **File output & naming**

- Reports are exported in Excel (.xlsx) format. Default file names follow predictable patterns:
  - Monthly Usage: `monthly_usage_[MONTH]_[YEAR]_[TIMESTAMP].xlsx` (e.g., `monthly_usage_december_2025_20251201_120000.xlsx`)
  - Date Range Usage: `[granularity]_report_[TIMESTAMP].xlsx` (e.g., `weekly_report_20251201_120000.xlsx`)
  - Inventory: `inventory_[report_type]_[TIMESTAMP].xlsx` (e.g., `inventory_stock_levels_report_20251201_120000.xlsx`)
  - Trends: `trends_report_[group_by]_[TIMESTAMP].xlsx` (e.g., `trends_report_item_20251201_120000.xlsx`)
- The application saves generated files to a dedicated `reports` folder inside the application's working directory. If the folder does not exist, it is created automatically on first export.
- The **Generated Reports** list shows exactly the `.xlsx` files found in that folder.

## **Status & results panels**

- **Status:** Shows progress, success, and error messages (e.g., "Generating report...", "✅ Report generated successfully!", or specific errors such as invalid date ranges or "No data found"). Failed report generation does not emit success messaging.
- **Generated Reports:** A live list of `.xlsx` files currently present in the dedicated reports folder.
- **Refresh:** Manually re-scan the reports folder for `.xlsx` files.
- **Open Report / Open Folder:** Actions below Generated Reports open the selected file or the reports folder.
- **Copy File:** Copies the selected report as a file object to clipboard so it can be pasted into Explorer, email attachment pickers, or supported targets.
- **Delete:** Removes the selected report file after confirmation and requires editor name/initials for audit logging.
- **Recent Reports:** A timestamped activity list of recent reports created by the application.

## **Validation & common warnings**

- **Date validation:** Start date must not be after end date. The UI shows a warning and cancels generation if invalid.
- **No data found:** If a report has no rows for the chosen criteria you will see a clear message in the status area and a dialog in some cases. Try widening the date range or removing restrictive filters.
- **Export failures:** If the app cannot write the file (permission, disk full, or other I/O errors) an error will be shown.

## **Quick recipes / common tasks**

- **Generate a monthly usage report:** Select **Usage Reports** → choose **Monthly Usage** → select year and month → set category filter (optional) → **Generate Report**.
- **Generate a date range usage report for last month:** Select **Usage Reports** → choose **Date Range** → set date range to **Last Month** → **Generate Report**.
- **Track material usage by grade level:** Select **Inventory Reports** → choose **Usage by Grade Level** → set date range → **Generate Report**.
- **Find low stock items:** Select **Inventory Reports** → choose **Low Stock Alert** → (optionally) toggle absolute threshold → **Generate Report**.
- **View edit history for items:** Select **Inventory Reports** → choose **Update History Report** → set date range → **Generate Report**.
- **Check for defective items returned:** Select **Inventory Reports** → choose **Defective Items Report** → set date range → **Generate Report**.
- **Create a trends report for top items:** Select **Trends Reports** → choose date range → set **Group By** to `Item` and **Top Items** to `Top 10` → **Generate Report**.

## **Zero-Stock Item Filtering**

Items with current stock of 0 (fully consumed or disposed) are automatically excluded from:

- Expiration alerts and reports
- Calibration alerts and reports
- Stock level reports
- Low stock warnings
- Dashboard alert indicators
- Inventory table color-coded status indicators (no warning colors shown for 0-stock items)

**Note:** Items remain in the database for historical purposes and requisition integrity. They are simply filtered from active monitoring and alert displays. Use historical reports to access disposed item records.

## **Limitations & notes**

- Reports are exported as Excel files and are intended for human review and simple data interchange. They are not a substitute for a full BI system.
- The application currently saves files to the working directory and does not prompt for a destination directory on every export.
- Generated Excel files use consistent, human-friendly headers and period labels to make them easy to read and compatible with spreadsheet analysis tools.
- Items with 0 stock are excluded from most alerts and reports; use history/disposal reports to review disposed items.

## **Troubleshooting & support**

- If opening a report fails, select the report and use **Open Folder**, then open the file manually from your file manager.
- If you get "No data found" and believe data should exist, try expanding the date range or removing filters. If results are still missing, contact your administrator and include the filters and date range you used.
- For repeated permission or I/O issues, check available disk space and file permissions for the application's working directory.
- If a selected report is deleted or moved externally, refresh the list (or wait for auto-refresh) and select an existing file again.

-- End of Reports Help --
