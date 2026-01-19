# Reports Help

The Reports page is where you generate, inspect, and export detailed, Excel-compatible reports about inventory, usage, and time-based trends. It provides flexible filters and options so you can create the exact dataset you need for auditing, stock management, or sharing with colleagues.

## **Top controls (header)**

- **🔄 Refresh:** Reloads the list of available categories, suppliers, and recent report metadata.
- **📅 Date range presets:** Quick presets such as **Last 7 Days**, **Last 30 Days**, **This Month**, **Last Month**, **This Year**, and **Last Year** let you set common ranges in one click.
- **🚀 Generate Report:** Start generation of the currently selected report with the chosen options. Report generation runs in the background and the UI displays progress messages.

## **Report Types & Tabs**

There are three main tabs: **Usage Reports**, **Inventory Reports**, and **Trends Reports**. Choose the tab that matches your need, configure options, and click **Generate Report**.

- **Usage Reports:** Time-bucketed usage of items across the selected date range. Use the **Report Type** dropdown to choose between **Monthly Usage** (grouped by week within a month, with category grouping) or **Date Range** (flexible date range with daily/weekly/monthly/quarterly granularity). Monthly Usage supports category filtering and is the default selection. The counts reflect actual laboratory activity dates (when materials were used in lab activities), not when they were borrowed.
- **Inventory Reports:** Several prebuilt inventory-focused exports including **Stock Levels Report**, **Expiration Report**, **Low Stock Alert**, **Acquisition History**, **Calibration Due Report**, **Update History Report**, **Disposal History Report**, **Usage by Grade Level**, and **Defective Items Report**. Some reports use date ranges (e.g., Acquisition History, Expiration windows). Others show current or historical state.
- **Trends Reports:** Time-series (pivoted) reports grouped by **Item** or **Category**, with Auto/manual **Granularity** (Daily/Weekly/Monthly/Quarterly), and an optional **Top N** filter (Top 10/20/50/All).

## **Filters & Options**

- **Date Range:** Use the date selector or quick presets to pick the report window. The UI validates start ≤ end and will warn if the range is invalid.
- **Category / Supplier filters (Usage/Inventory):** Restrict the report to a subset of items.
- **Include consumables:** Toggle whether consumable items are included in Usage/Trends reports.
- **Low Stock Threshold (Inventory → Low Stock Alert):** By default the application uses percentage-based thresholds (Consumables 20% / Non-consumables 10%). You can opt to supply an absolute unit threshold by toggling the percentage-mode checkbox and entering a number.
- **Granularity (Trends):** The system auto-selects a sensible granularity based on the length of the date range. You can override using the Granularity menu. Hover the granularity control for an explanation of how the Auto selection works.
- **Group By / Top N (Trends):** Group by `Item` or `Category` and optionally limit the output to the top N items by usage.

## **What each report contains (at-a-glance)**

- **Monthly Usage Report:** Items grouped by category with weekly breakdown for a selected month. Includes columns: ITEMS, CATEGORIES, ACTUAL INVENTORY, SIZE, BRAND, OTHER SPECIFICATIONS, WEEK 1-4, and Total Usage. Professional layout matching laboratory standards.
- **Date Range Usage Report:** Period-by-period breakdown of quantity moved/used per item (columns represent time-period buckets determined by granularity). Headers and period labels are formatted for readability (title-case and human-friendly period labels). Filtered by category.
- **Stock Levels Report:** Current stock per item (includes total and available quantities where appropriate). Useful for stock-taking and audits. Shows separate counts for consumables (with consumption deduction) and non-consumables (showing original stock).
- **Expiration Report:** Items and batches expiring inside the selected window, with dates and batch details where available.
- **Low Stock Alert:** Items below the configured threshold. When using percentage mode it applies 20%/10% defaults depending on item type.
- **Acquisition History:** Incoming/received batches and quantities during the date range, with batch sequence labels (B1, B2, B3, etc.).
- **Calibration Due Report:** Non-consumable items with calibration due within the selected window.
- **Update History Report:** Complete history of all edits to inventory items within the date range, including who edited (editor name), when, and reason for editing.
- **Disposal History Report:** Profile of disposed/deleted items with disposal date, reason, who disposed them, and category grouping.
- **Usage by Grade Level:** Usage breakdown by requester grade level and section, showing lab activity name and date. Useful for tracking material usage across different educational groups.
- **Defective Items Report:** Items reported as defective or damaged during requisition returns, including condition type, quantity, notes, and who reported.
- **Trends Reports:** Pivoted time-series tables where rows are items or categories and columns are period buckets (daily, weekly, monthly, etc.) depending on granularity.

## **File output & naming**

- Reports are exported in Excel (.xlsx) format. Default file names follow predictable patterns:
  - Monthly Usage: `monthly_usage_[MONTH]_[YEAR]_[TIMESTAMP].xlsx` (e.g., `monthly_usage_december_2025_20251201_120000.xlsx`)
  - Date Range Usage: `[granularity]_report_[TIMESTAMP].xlsx` (e.g., `weekly_report_20251201_120000.xlsx`)
  - Inventory: `inventory_[report_type]_[TIMESTAMP].xlsx` (e.g., `inventory_stock_levels_report_20251201_120000.xlsx`)
  - Trends: `trends_report_[group_by]_[TIMESTAMP].xlsx` (e.g., `trends_report_item_20251201_120000.xlsx`)
- The application saves the file to the application's working directory and will attempt to open it automatically (on Windows the app uses the OS to open the file). If automatic opening fails, the saved file path is shown in the status area so you can open it manually.

## **Status & results panels**

- **Status:** Shows progress, success, and error messages (e.g., "Generating report...", "✅ Report generated successfully!", or specific errors such as invalid date ranges or "No data found").
- **Generated Reports:** A short list of generated files from the current session for quick reference.
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

- If automatic opening fails, check the Status box for the saved file path and open it from your file manager.
- If you get "No data found" and believe data should exist, try expanding the date range or removing filters. If results are still missing, contact your administrator and include the filters and date range you used.
- For repeated permission or I/O issues, check available disk space and file permissions for the application's working directory.

-- End of Reports Help --
