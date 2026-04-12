# Inventory Page

The Inventory page is the main workspace for item records, stock visibility, and item-level maintenance.

## What This Page Handles

- View inventory rows with stock and alert context.
- Add, edit, delete, and import items.
- Search and filter by text, category, supplier, item type, lifecycle status, and acquisition date range.
- Surface date-based alert states through row coloring.
- Open per-item usage history directly from the inventory table.
- Open and maintain Safety Data Sheets (SDS) for chemical items.

Underlying tables involved are `Items`, `Item_Batches`, and `Stock_Movements`.

## Loading and Performance

- Data loads asynchronously to keep the UI responsive.
- A thin loading indicator is shown at the bottom of the page while refresh is in progress.
- Post-query processing (item row shaping and status prefetch) runs in a background worker before UI binding.
- Large inventory result sets bind to the table in progressive row batches, so rows become visible incrementally instead of appearing only after full render.
- Status color styling is applied in phases (essential first, full pass second) to keep first paint responsive.
- Statistics cards refresh in a background worker and can complete independently of table row rendering.
- Progress bar now remains active through inventory table population/styling so long refreshes have visible feedback.
- Action buttons are temporarily guarded during critical load phases.
- Virtual scrolling exists as an internal feature flag and is not currently exposed as a user setting.

## Importing Items

Use `Inventory -> Import Items` for bulk creation from `.xlsx` files.

Required input fields (with flexible header matching):

- item name
- stock value
- item type

The importer supports case-insensitive and spacing-tolerant header matching and can detect headers below title rows. For full details, see `docs/importing_items.md`.

## Item Lifecycle

- Create: stores item data and initial batch quantity.
- Edit: updates item data and writes update history.
- Edit (existing items): includes Batch Acquisition Records management for adding, editing, and removing batch entries (`B1`, `B2`, `B3`, and so on).
- Delete: requires editor attribution and reason; blocked for currently requested items.
- Add/Edit validation: Name, Category, and Editor Name/Initials are required before save.
- Add flow duplicate warning: when another item exists with the same normalized name in the same category, the app shows a warning and lets users continue or cancel.
- Supplier is optional, but if provided it must be selected from the Supplier dropdown.
- Supplier, Size, Brand, and Category reference values are managed through Settings; in-use Size/Brand/Supplier values are non-deletable and display usage state there.
- Size input is editable with suggestions: users can select existing values or type a new size directly in Add/Edit Item.
- Typed size values are normalized to metric casing (for example, `10 mL`, `2.5 L`, `125 g`) before save.
- If optional dropdowns are left blank (Supplier, Size, Brand), a confirmation dialog lists them before save. Users can proceed or go back to fill entries.

Double-clicking an inventory row opens the item usage history dialog. Use the `Edit Item` button for field edits.

Chemical rows (`Chemicals-Solid`, `Chemicals-Liquid`) show an `SDS` action beside the item name. If an SDS file exists, clicking it opens that exact file externally. If no SDS entry exists, the app shows a message indicating SDS is required.

Categories are fixed by system configuration and determine default item type/date behavior.

## Inventory Fields

- Brand, Supplier, Other Specifications, Expiry/Disposal Date, Item Type, and Acquisition Date are supported in add/edit and import flows.
- Supplier values are stored by `supplier_id` and resolved from supplier names during import.
- Size values are normalized to canonical metric casing in manual and import flows.
- Manual add/edit treats the default `Select Supplier` as no supplier (`NULL`), not a text value.
- Unselected optional dropdowns (Supplier, Size, Brand) are stored empty and displayed as `N/A` in the inventory table.
- Item type is persisted as text in `Items.item_type` (`Consumable`, `Non-consumable`, or `TA, non-consumable`) and synchronized with `is_consumable` for stock behavior.
- Chemical items support SDS metadata in `Item_SDS` (stored filename, original filename, path, MIME type, optional notes, and editor attribution).

## Batch Acquisition Records

- Multi-batch acquisition is stored in `Item_Batches` with sequential labels (`B1`, `B2`, `B3`, and so on).
- Each batch stores its own `date_received` and `quantity_received` values.
- Existing item edits support batch record maintenance:
  - Add a new batch with date and quantity.
  - Edit date/quantity for an existing batch.
  - Remove a batch only when it has no stock movement history.
- Item-level `Items.acquisition_date` remains as a compatibility fallback and is synchronized to the earliest batch date.

## SDS Management

- SDS files are stored locally in an `sds/` folder beside the running application.
- In Add/Edit Item, chemical categories expose optional SDS file and SDS notes fields.
- In the inventory table, only chemical rows display the SDS action button for quick external open.
- During table refreshes after edits/filter changes, inline SDS name widgets are fully rebuilt per row so stale labels do not overlap other rows.
- Selecting a chemical row reveals a toolbar `SDS Settings` button. Use this button to upload, update, or remove SDS entries.
- All SDS save/update/remove actions require editor attribution and are logged to `Update_History`.

## Auto-Calculated Dates

When category and acquisition date are set, default dates are auto-filled:

- Consumables: expiration date from category shelf-life rule.
- Non-consumables: disposal date from category lifespan rule.
- Equipment only: calibration date (initially one year from acquisition).
- For non-consumables, `calibration_date` is treated as the last calibration date; next due is computed as +1 year.

Users can manually override dates before saving.

## Alert and Color Rules

Status computation rules:

- Consumable expiration warning: within 180 days.
- Non-consumable disposal warning: within 90 days.
- Equipment calibration warning: within 90 days of next due date.
- Overdue when the relevant due date is already in the past.

Non-consumable disposal evaluation is batch-aware:

- If an item has batch records, disposal status is calculated per batch (using batch disposal date when present, or category lifecycle from batch received date).
- The most urgent batch drives the row-level status and color.
- Alert surfaces include the batch label (`B1`, `B2`, and so on) for disposal-related entries.

Row coloring:

- Red/pink: overdue.
- Yellow: warning.
- Default: no current alert.

If multiple statuses apply, the most critical one determines row color.

## Zero-Stock Behavior

Items with `0` current stock remain stored for history and requisition integrity, but they are excluded from active alert calculations.

## Stock Computation Summary

- Consumables: stock changes with issue/return/disposal movements.
- Non-consumables: item count is effectively retained while movement history tracks usage and returns.
- Defective reports reduce current usable availability until confirmed.
- Defective confirmation outcomes:
  - `Not Defective`: returns quantity to current usable availability.
  - `Disposed`: permanently reduces total stock.

The system prevents stock from going negative.

## Standard Categories

- Chemicals-Solid
- Chemicals-Liquid
- Prepared Slides
- Consumables
- Equipment
- Apparatus
- Lab Models
- Others
- Uncategorized

## Search, Filters, and Usage History

- Search is case-insensitive and matches item name, category, and supplier text.
- Search and filter controls use responsive horizontal sizing and expand to fill available panel width.
- Category, supplier, and item type filters are exact-match dropdown filters.
- Status filter supports `Expiring`, `Expired/Overdue`, `Calibration Warning`, and `Calibration Due`.
- Filters compose as intersection logic. Applying multiple filters narrows to rows that satisfy all active criteria.
- Acquisition date range filter is optional and filters by `Items.acquisition_date` when enabled.
- Acquisition date range filter is optional and batch-aware when batch records exist: an item matches when any batch acquisition date falls inside the selected range.
- `Clear Filters` resets all filters and returns the full inventory list without forcing a reload.
- Double-click an item row to open usage history. The history view includes requisition usage events and defective/broken return events.
- History defaults to all-time. Users can enable a date range and filter by activity/reported date.
- The `Show Defective Events Only` toggle is always available in usage history.
- Defective confirmations (`Disposed` and `Not Defective`) are always available in usage history when an actionable defective row is selected.
- After a defective confirmation is applied, the inventory page refreshes automatically so stock and DEF indicators stay in sync.
