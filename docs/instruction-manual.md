# Laboratory Inventory Manager — Instruction Manual

This instruction manual explains how to use the Laboratory Inventory Manager desktop application (standalone EXE created with PyInstaller) and how to manage inventory using the system.

## Quick Start

- Double-click the provided executable The app launches the GUI immediately.
- On first run, the app will automatically initialize the SQLite database. By default, `inventory.db` is created in the same folder as the executable. A `logs` folder and `logs/logs.txt` file will be created automatically.

## Application Layout

The UI main sections (accessible via sidebar navigation) are:

- **Dashboard** — high-level metrics, alerts, and activity history.
- **Inventory** — item and batch management, stock counts, filters, and statuses.
- **Requisitions** — create and manage requests for inventory items, view lifecycle (requested → active → returned/overdue).
- **Requesters** — manage personnel allowed to submit requisitions.
- **Reports** — generate and export reports (Excel-compatible) for inventory and usage.
- **Settings** — manage supporting metadata (brands, categories, suppliers, sizes).

## Initial Setup

- Open the **Settings** page and ensure that supporting data (categories, suppliers, brands, sizes) are entered. These populate dropdowns on Item creation.
- Add any necessary **Requesters** (people who will request inventory) from the **Requesters** page.
- Confirm the Dashboard metrics look correct and that no critical alerts demand immediate attention.

## Inventory Management

- **Add Item**: Navigate to Inventory → `Add Item`.
  1. Fill required fields (Name, Category, Size, Brand, Supplier, Consumable, etc.).
  2. Optionally add Batch information (batch number, acquisition date, expiration date).
  3. Save to add item to the database. Audit details will record who added the item.

- **Edit Item**: Double-click the row in the Inventory table or use Edit Item action.
  1. Modify fields then Save. Note dependency checks: certain fields that would break historical integrity (like changing batch-related info for existing movement history) will be validated.

- **Delete Item**: Use Delete Item action; the system prevents deletions if related requisitions or stock movements exist.

- **Stock Movement** — Adding/consuming stock:
  - Use Stock Movement entry or create a Requisition to reserve items.
  - The Stock Movement system uses standardized movement types (issue, return, add, adjust, reserve).

- **Low Stock and Alerts**:
  - Items with low stock, expired stock, or calibration due will show alerts on the Inventory page and Dashboard.
  - Use Filters to show expiring or low-stock items and take corrective action (add stock, reorder, or perform recalibration).

## Requisitions Workflow

- **Creating Requisition** (Requester-based): Requisitions connect a requester with items they request.
  1. Go to Requisitions → New Requisition.
  2. Select a Requester (existing); if needed, create a requester from `Requesters` page.
  3. Add item lines (choose items and the required quantity). The system checks available stock.
  4. Confirm and submit the requisition. If stock is insufficient, the UI will prevent creating the requisition or will show warnings.

- **Processing Requisition**:
  - When approved/processed, items are reserved or issued depending on internal workflow.
  - Use the Requisition preview to mark items as returned or consumed and to register partial returns.

- **Returns**:
  - To process a return, open the Requisition preview and select the items being returned, choose the return reason, and set the returned quantities. The app records an activity entry for audit.

- **Validation**:
  - Requisitions perform stock validation and atomic transactions; the app uses immediate transactions to ensure accurate stock during simultaneous operations.

## Requesters

- Create and Edit Requesters from the Requesters page.
- Assign contact details and other metadata as needed.
- Requester records are used in the Requisition creation flow.

## Reports

- Access the Reports page and configure filters (date range, item, requester, movement type).
- Generate and export to Excel-compatible formats for review or recordkeeping.
- Typical reports include stock sheets, usage logs, movement history, and audit logs.

## Settings

- Manage categories, suppliers, brands, sizes and other metadata.
- Settings values are used as dropdowns across forms.

## Data and Files

- **Database** — `inventory.db` (SQLite). It will be in the working directory where the EXE is run.
- **Logs** — `logs/logs.txt`. Useful for troubleshooting; contains messages from the application.
- **Generated Reports** — saved by the application to the folder you select from within the Report export dialog.
- **Backups** — recommended to copy `inventory.db` to a secure location regularly.

## Backups & Database Management

- Regularly copy `inventory.db` to a secure backup folder.
- To restore, stop the application and replace the current `inventory.db` with your backup copy.
- To export/import data programmatically, use provided scripts or use a direct SQL client (SQLite) but always take a backup first.

## Troubleshooting

- **Application fails to start**: Check `logs/logs.txt` in the application folder for stack traces.
- **DB fails to initialize**: Ensure the folder is writable. If the app cannot create `inventory.db`, you may see errors in logs.
- **Concurrent access issues**: Avoid running multiple copies of the EXE working against the same DB concurrently. For multi-user setups consider converting to a central server DB.

## Common Errors & Fixes

- "Database file not found" — Run EXE in the same folder as the DB or place `inventory.db` in that folder.
- "Permission error creating database" — Ensure app folder is writable and not protected by the OS or an antivirus tool.

## Frequently Asked Questions

- Q: Where is the data stored?
  - A: In `inventory.db` inside the application working directory.
- Q: How do I create user accounts?
  - A: This release doesn't implement multi-user authentication; requesters are simply persons who can request items. Use Requesters page to manage them.
- Q: Can I export an item list?
  - A: Use Reports to generate and export item lists and stock reports.
