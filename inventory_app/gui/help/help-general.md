# General Help

Welcome to the Laboratory Inventory Monitor — this page gives non-technical, practical guidance for everyday use.

## What is this for?

- Track and manage laboratory items, batches, and stock levels.
- Record and process requisitions (requests for items) and returns.
- Keep a short activity log and generate Excel-compatible reports for export and auditing.

## Where to find help

- Use the **Help** tab (this page) for topic-specific instructions: Dashboard, Inventory, Requisitions, Requesters, Reports, Settings.
- For administrators: logs are stored in `logs/logs.txt` and the main database file is `inventory.db` in the application folder.

## Navigation (quick orientation)

- Left-hand navigation selects pages: **Dashboard**, **Inventory**, **Requisitions**, **Requesters**, **Reports**, **Settings**, **Help**.
- Most pages have a **Refresh** button — use it if data looks out of date.

## Common tasks

- Add an item: Go to **Inventory** → `➕ Add Item`. Select a category (dates will auto-populate based on category), fill the form, and save.
- Edit an item: Select a row and click `✏️ Edit Item`, or double-click a row to open the editor.
- Delete an item: Select it and click `🗑️ Delete Item`. You will be asked for your name and a reason. Deletion is permanent — use caution.
- Search & filters: Use the search box and filters (Category, Supplier, etc.) on the Inventory and Requisitions pages to narrow results.
- Work with requisitions: **Requisitions** → `➕ New Requisition` to create; select a requisition to `✏️ Edit`, `↩️ Return Items` (finalize and lock), `🖨️ Print` (export to HTML and print), or `🗑️ Delete` (requires editor name).
- Manage requesters: **Requesters** → `➕ Add Requester` to register people who can request items. You cannot delete a requester if they have recorded requisitions.
- Generate exports: **Reports** → choose a report type (Monthly Usage, Stock Levels, Defective Items, Update History, etc.), set date range and filters, then click `🚀 Generate Report`. Reports are saved as Excel files and may open automatically.
- Manage lookup lists: **Settings** → Add/Edit/Delete Sizes, Brands, and Suppliers. Categories are **predefined and fixed** and cannot be modified. These values populate dropdowns across the app.

## Important behaviors & rules

- Deletions and some edits require you to enter **your name/initials** for the audit trail.
- Some operations are blocked by database constraints (for example, returning more items than were requested). If an operation fails the app will show an error dialog — check `logs/logs.txt` for more detail.
- When a requisition is `returned` (finalized), it becomes locked: edit and return actions are disabled.
- The Dashboard is an overview only — use the Inventory, Requisitions, or Reports pages to act on records.

## Reports & files

- Reports are Excel-compatible (.xlsx) files. Filenames include the report type and timestamp for easy identification.
- If exporting fails (permissions, disk full, or I/O error) you will see an error dialog.

## Data safety & backups

- The application uses a local SQLite database file named `inventory.db` by default (created in the app folder on first run).
- Back up your data by copying `inventory.db` to a secure location regularly.
- To restore: stop the application and replace the current `inventory.db` file with your backup copy.

## Troubleshooting (quick checks)

- App won't start: Check `logs/logs.txt` in the application folder for messages and stack traces.
- Data load/export errors: Ensure the application folder is writable and there's enough disk space; check `logs/logs.txt` for details.
- Repeated or unclear failures: Note the action and timestamp, then contact your administrator with the `logs/logs.txt` file.

## Tips & shortcuts

- Double-click an inventory row to open the edit dialog quickly.
- Tooltips explain why a button may be disabled (hover over the control to read it).

## Glossary (short)

- Requisition: A request for one or more items by a registered requester.
- Requester: A person or group recorded in the system who can make requisitions.
- Batch: A recorded receipt or grouping of items (used for tracking expiry, stock by batch).
- Consumable: Items that are consumed when used (stock decreases permanently when used).
- Available stock vs Total stock: Available stock is what can be requested now; total stock includes reserved, damaged, or otherwise unavailable quantities as calculated by the system.

If you need more detailed, step-by-step instructions, visit the other help topics in the **Help** tab or contact your administrator with the log file and a brief description of the problem.

-- End of General Help --
