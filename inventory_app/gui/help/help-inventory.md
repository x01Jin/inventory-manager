# Inventory Help

The Inventory page is the primary place to view, search, and manage all items, batches, and stock information in the system. This help page describes every user-facing control, what the numbers mean, and how to perform the common tasks you will need.

## **Top controls (header)**

- **➕ Add Item:** Opens the Item Editor to add a new item and (for new items) an initial batch quantity. Required: Item name, Category, and Editor name/initials.
- **✏️ Edit Item:** Enabled when you select a row; opens the Item Editor to edit the selected item.
- **🗑️ Delete Item:** Enabled when you select a row; prompts for confirmation and requires your name/initials and a deletion reason. Deletions are permanent.
- **🔄 Refresh:** Reloads items, filters, and statistics from the database.
- **⬇️ Import Items:** Opens the Import dialog to import items from an `.xlsx` (Excel) file. Use this to add many items at once; each imported row creates a new Item and an initial batch unless skipped.
- **SDS (row action):** Appears beside item names only for chemical rows (`Chemicals-Solid` and `Chemicals-Liquid`). If SDS exists, it opens the exact SDS file externally. If SDS does not exist, the app shows a message that SDS entry is required.
- **🧪 SDS Settings (toolbar):** Appears when a chemical row is selected. Use this button to upload, update, or remove SDS records.

## **Importing items (Excel .xlsx) 🔧**

1. **Open Import → Choose file:** Select an `.xlsx` file. Only Excel files are accepted (use the Excel Files (*.xlsx) filter).
2. **Editor name (required):** Enter your name or initials — this is recorded in the audit trail for each created item.
3. **Resolve missing consumable units (when prompted):** If consumable rows contain decimal `stocks` with no unit (for example `1.5`), the app shows a review table where you can choose a unit (`ml`, `L`, `mg`, `g`, `kg`) or **Skip row** for each flagged entry.
4. **Start import:** Click **Continue Import** in the review dialog (or **Import** directly when no rows are flagged).
5. **Progress & cancel:** The dialog shows a live progress bar and status label like `[current/total], skipped: X`. You can cancel the import at any time using **Cancel Import** — already-processed rows remain.
6. **Result:** On completion the dialog shows counts of imported and skipped rows and a short confirmation pop-up.

**Important details:**

- **Header detection:** The importer scans the first **40 rows** of the active worksheet to find the header row so you may include title/notes above the table. Header names are matched case- and space-insensitively (for example `Item Name`, `itemname`, or `name` are equivalent).
- **Minimum required columns:** `name` (or `item` / `items`), `stocks`, and `item type`. If these are missing the import aborts with an error telling you which columns are missing.
- **Stocks parsing:** The importer accepts a variety of free-form `stocks` values. Size-bearing entries like `900ml`, `1.1 L`, `1.1 gal`, `2 liters`, `1 kilo`, and `125 gms` are treated as **usable quantities** and the parsed size is used as the item `size` when an explicit `size` column is empty. For larger units, the importer converts to base usable units (`1 L` -> `1000`, `2.5 L` -> `2500`, `1.1 gal` -> `1100`, `1 kilo` -> `1000`) so requisitions can borrow partial amounts while still using integer quantities. Parsed size values are normalized to canonical unit casing (for example, `900 mL`, `1 kg`, `125 g`). Package entries with piece details like `1 box (100pcs)` or `2 packs of 50 pcs` are converted to usable quantity using `packages * pieces` (for example, `1 box (100pcs)` -> quantity `100`). Invalid or unparseable stock values cause the row to be **skipped** and the reason is recorded in the import log.
- **Missing-unit prompt:** Before import starts, consumable rows with decimal stocks and no explicit unit are flagged (example: `1.5`). You can select a unit per row from a dropdown (`ml`, `L`, `mg`, `g`, `kg`) or skip that row.
- **Consumables tip:** Requisition and return use integer quantities. If you need partial-use tracking (for example 100 ml from a 900 ml item), make sure stock is in usable units.
- **Item type / category handling:** `Item type` is normalized (e.g., values containing `non` + `consum` are treated as Non-Consumable). The normalized value is saved as `Consumable`, `Non-consumable`, or `TA, non-consumable` and synchronized with stock behavior. If a `category` value is provided the importer will match an existing category case-insensitively; unknown, empty, or `N/A` categories are mapped to `Uncategorized`.
- **Supplier handling:** Supplier names from import are resolved case-insensitively against existing suppliers. Missing supplier names are added automatically and then linked to imported items.
- **Row-level errors:** Rows with validation or DB errors are skipped. On unexpected DB errors the importer reports the row as failed and continues processing subsequent rows where possible.

**Tips:**

- Use this import for fast bulk creation of simple items and an initial batch; for per-item advanced batch data (multiple batches, batch dates), import basic rows and then edit items manually or use the programmatic APIs.
- If an import repeatedly fails, attach the **debug log** lines that show save parameters and error messages when asking for help.

## **Filters & Search**

- **🔍 Search:** Search by item name, category, or supplier. Typing updates the table instantly.
- **📂 Category:** Filter the table to a single category or choose **All Categories** to show everything.
- **🏢 Supplier:** Filter the table to a single supplier or choose **All Suppliers**.
- **🧪 Item Type:** Filter by `Consumable`, `Non-consumable`, or other configured item type values.
- **Acquisition Date Range:** Enable **Filter by acquisition date** and set From/To dates to show only items acquired in that range.
- **🗑️ Clear Filters:** Resets search and filter controls and restores the full inventory list.

All active filters are combined. The table shows only rows that satisfy every selected filter.

## **Inventory Table (columns & meanings)**

The table shows one row per item/batch grouping. Column list and descriptions:

- **Stock/Available:** Shown as `total/available`. `total` is received batches minus consumed/disposed plus returns; `available` subtracts active reservations/requests so it reflects what can be allocated now.
- **Name:** Item display name. Click to select a row; double-click to open usage history.
- **SDS button beside Name (chemicals only):** Quick-open action for external file viewing. Missing entries show an SDS-required message.
- **Size / Brand / Other Specifications:** Size supports dropdown suggestions and direct typed entry; brand and other specifications remain free-form.
- **Supplier:** Supplier name (if provided).
- **Calibration Date:** For non-consumables, shows last calibration date.
- **Expiry/Disposal Date:** For consumables this is expiration; for non-consumables this is disposal date.
- **Item Type:** `Consumable` or `Non-Consumable` — affects which date is shown (expiration vs calibration/disposal).
- **Acquisition Date:** When the item or batch was acquired.
- **Last Modified:** Timestamp of the most recent change (format `MM/DD/YYYY HH:MM`).

Notes about sorting and selection:

- Click any column header to sort. The table applies sensible defaults: stock shows highest availability first, names sort A→Z, and date columns default to newest-first.
- Select a row to enable **Edit** and **Delete** buttons.

## **Color coding & alerts (what the colors mean)**

The inventory table uses row background colors to indicate items requiring attention based on their expiration, disposal, or calibration status:

- **Overdue (reddish pink background):** Item is past its expiration or disposal date, or calibration is overdue.
- **Warning (pale yellow background):** Disposal/expiration or calibration is approaching.
- **Default (no special color):** No immediate alert.

For non-consumable items with both disposal and calibration dates, the most critical status determines the row color (e.g., if an item has both calibration warning and expired disposal date, the row will show the overdue color).

Alert thresholds (how statuses are derived):

- **Consumables:** Items with an expiration date <= 180 days (6 months) are flagged as warnings; dates already past are marked as overdue.
- **Non-Consumables:** Calibration next-date within 90 days is a warning; overdue is marked as overdue. Disposal within 90 days is a warning; already past disposal is marked as overdue. When multiple alerts apply, the most critical determines the row color.

## **Item Editor (Add / Edit)**

Key fields and behaviors in the Add/Edit dialog:

- **Name (required):** The visible name of the item.
- **Category (required):** Select from predefined categories (Chemicals-Solid, Chemicals-Liquid, Prepared Slides, Consumables, Equipment, Apparatus, Lab Models, Others, or Uncategorized). Changing category automatically calculates item type plus default expiration/disposal dates, and calibration date where applicable. You can still manually adjust these dates afterward.
- **Supplier / Size / Brand:** Select suppliers from existing entries. Size supports suggestions plus direct typed entry and is normalized to metric unit casing (for example, `500 mL`). Brands remain dropdown-based.
- **PO Number:** Optional purchase order number.
- **Batch Quantity (Add only):** Number of units/batches to record for a new item. Must be a positive integer. Defaults to 1.
- **Other Specifications:** Free-form text for details (materials, model numbers, notes).
- **SDS File (chemical categories only):** Optional file chooser used to attach a local SDS file while adding/editing a chemical item.
- **SDS Notes (chemical categories only):** Optional notes for hazard/first-aid/handling summaries.
- **Acquisition Date:** Defaults to today; you may change it. **Changing this date recalculates expiration/calibration dates** based on the category thresholds.
- **Item Type:** Automatically set by category selection (Consumable or Non-Consumable). You can override this manually if needed. This toggles the meaning of the date fields:
  - If **Consumable**, the bottom-right date is **Expiration Date** (special value `No Expiration` allowed).
  - If **Non-Consumable**, the top-right date becomes **Disposal Date** and the bottom-right becomes **Calibration Date** (each can be left unset / special value to indicate None).
- **Editor Name/Initials (required):** You must supply this for audit purposes when saving or deleting.
- **SDS audit requirement:** SDS save/update/remove actions require editor attribution and are written to update history.

**Auto-calculated dates explained:**

When you select a category, dates are automatically calculated using industry standards:

- **Chemicals (Solid/Liquid):** Expiration set to 24 months (2 years) from acquisition date; alerts appear 6 months before expiration
- **Prepared Slides:** Expiration set to 36 months (3 years) from acquisition date
- **Consumables:** Expiration set to 12 months (1 year) from acquisition date
- **Equipment:** Disposal set to 5 years from acquisition; Calibration set to 1 year from acquisition
- **Apparatus / Glassware:** Disposal set to 3 years from acquisition; no calibration schedule by default
- **Lab Models / Others:** Disposal set to 5 years from acquisition
- **Uncategorized:** No automatic date calculation

You can always edit these dates manually if the calculated values don't match your laboratory's specific requirements.

Validation & messages:

- Saving will show warnings for missing required fields (item name, category, editor name) and for invalid batch quantities.
- In Add Item flow, if another item in the same category has the same normalized name, the app shows a likely-duplicate warning and lets you continue or cancel.
- Supplier is optional, but if selected it must come from the Supplier dropdown list.
- If optional dropdown fields are left blank (Supplier, Size, Brand), the app shows a confirmation dialog listing those fields. You can proceed with save or go back and fill them.
- Optional dropdowns left blank are displayed as `N/A` in the inventory table.
- Successful saves show a confirmation message. Errors will show an error dialog with details.

## **Delete behavior**

- Deleting an item prompts for confirmation and requires you to enter `Editor Name` and a deletion reason. The action is recorded for audit and cannot be undone.

## **Statistics (Quick Statistics panel)**

The Quick Statistics block shows several counts and small alerts:

- **Total Batches:** Count of received batches in the system.
- **Total Stock:** Sum of current stock across batches (applies the same stock calculations used in the table).
- **Available Stock:** Total stock minus active reservations/requests.
- **Low Stock:** Count of items with current stock < 10 and > 0 (simple absolute threshold used for the quick metric).
- **Expiring / Expired / Cal. Warning / Cal. Overdue:** Counts produced by the item status service, and may include combined counts where items match multiple alert conditions.

## **Search & Filter behavior (exact matching rules)**

- The **Search** box matches text inside `name`, `category`, or `supplier` (case-insensitive, substring match).
- Category, Supplier, and Item Type filters are exact matches based on dropdown values.
- Date-range filtering applies to acquisition date when enabled.
- Filters are intersection-based and do not overwrite each other.

## **Item Usage History**

- Double-click an inventory row to open its usage history dialog.
- The dialog shows item usage events from requisitions and defective/broken return events.
- Each history row includes requester name, grade/section, activity date, lab activity, quantity, request/return dates, and notes.
- Default view is all-time. Enable date range in the dialog to filter by date.

## **How available stock is calculated (brief, factual)**

- `Total Stock` follows item-type rules:
  - Consumables: `received - consumption - disposal + return`
  - Non-consumables: `received - disposal` (borrow/request and return do not permanently change stock)
- `Available Stock` subtracts active reservations/requests so it reflects what can actually be allocated now.

## **Common tasks / quick recipes**

- **Add a new item:** Click **➕ Add Item**, fill the required fields (name, editor), set batch quantity and any dates, save.
- **Edit an item:** Select its row and click **✏️ Edit Item**, change fields, and save.
- **Delete an item:** Select row → **🗑️ Delete Item** → confirm, enter your name and reason → Delete.
- **Find items:** Use the **🔍 Search** box and the Category/Supplier filters together to narrow results.
- **Investigate an alert:** Sort or filter by dates, double-click item to inspect usage history, or use **✏️ Edit Item** to inspect calibration/expiration/disposal fields.

## **Limitations & notes**

- The Inventory page is authoritative for item records and batches — use `Reports` for advanced exports and `Requisitions` for reservation history or to examine requests.
- The table display is optimized for readability; some long text fields (other specifications) may be truncated for layout reasons — open the item editor to see full text.
- If an operation fails (save/delete/refresh), an error dialog will appear. If that happens repeatedly, contact your administrator and include the action and time — the system logs provide further details.

-- End of Inventory Help --
