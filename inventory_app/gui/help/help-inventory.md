# Inventory Help

The Inventory page is the primary place to view, search, and manage all items, batches, and stock information in the system. This help page describes every user-facing control, what the numbers mean, and how to perform the common tasks you will need.

## **Top controls (header)**

- **➕ Add Item:** Opens the Item Editor to add a new item and (for new items) an initial batch quantity. Required: Item name and Editor name/initials.
- **✏️ Edit Item:** Enabled when you select a row; opens the Item Editor to edit the selected item. You can also double-click a row to edit.
- **🗑️ Delete Item:** Enabled when you select a row; prompts for confirmation and requires your name/initials and a deletion reason. Deletions are permanent.
- **🔄 Refresh:** Reloads items, filters, and statistics from the database.
- **⬇️ Import Items:** Opens the Import dialog to import items from an `.xlsx` (Excel) file. Use this to add many items at once; each imported row creates a new Item and an initial batch unless skipped.

## **Importing items (Excel .xlsx) 🔧**

1. **Open Import → Choose file:** Select an `.xlsx` file. Only Excel files are accepted (use the Excel Files (*.xlsx) filter).
2. **Editor name (required):** Enter your name or initials — this is recorded in the audit trail for each created item.
3. **Start import:** Click **Import**. The import runs in a **background thread** so the UI remains responsive.
4. **Progress & cancel:** The dialog shows a live progress bar and status label like `[current/total], skipped: X`. You can cancel the import at any time using **Cancel Import** — already-processed rows remain.
5. **Result:** On completion the dialog shows counts of imported and skipped rows and a short confirmation pop-up.

**Important details:**

- **Header detection:** The importer scans the first **40 rows** of the active worksheet to find the header row so you may include title/notes above the table. Header names are matched case- and space-insensitively (for example `Item Name`, `itemname`, or `name` are equivalent).
- **Minimum required columns:** `name` (or `item` / `items`), `stocks`, and `item type`. If these are missing the import aborts with an error telling you which columns are missing.
- **Stocks parsing:** The importer accepts a variety of free-form `stocks` values. Size-bearing entries like `900ml`, `1.1 L`, `2 liters`, `1 kilo`, and `125 gms` are treated as **usable quantities** and the parsed size is used as the item `size` when an explicit `size` column is empty. For larger units, the importer converts to base usable units (`1 L` -> `1000`, `2.5 L` -> `2500`, `1 kilo` -> `1000`) so requisitions can borrow partial amounts while still using integer quantities. Package entries with piece details like `1 box (100pcs)` or `2 packs of 50 pcs` are converted to usable quantity using `packages * pieces` (for example, `1 box (100pcs)` -> quantity `100`). Invalid or unparseable stock values cause the row to be **skipped** and the reason is recorded in the import log.
- **Consumables tip:** Requisition and return use integer quantities. If you need partial-use tracking (for example 100 ml from a 900 ml item), make sure stock is in usable units.
- **Item type / category handling:** `Item type` is normalized (e.g., values containing `non` + `consum` are treated as Non-Consumable). If a `category` value is provided the importer will match an existing category case-insensitively; unknown, empty, or `N/A` categories are mapped to `Uncategorized`.
- **Row-level errors:** Rows with validation or DB errors are skipped. On unexpected DB errors the importer reports the row as failed and continues processing subsequent rows where possible.

**Tips:**

- Use this import for fast bulk creation of simple items and an initial batch; for per-item advanced batch data (multiple batches, batch dates), import basic rows and then edit items manually or use the programmatic APIs.
- If an import repeatedly fails, attach the **debug log** lines that show save parameters and error messages when asking for help.

## **Filters & Search**

- **🔍 Search:** Search by item name, category, or supplier. Typing updates the table instantly.
- **📂 Category:** Filter the table to a single category or choose **All Categories** to show everything.
- **🏢 Supplier:** Filter the table to a single supplier or choose **All Suppliers**.
- **🗑️ Clear Filters:** Resets search and filter controls and reloads the full inventory.

## **Inventory Table (columns & meanings)**

The table shows one row per item/batch grouping. Column list and descriptions:

- **Stock/Available:** Shown as `total/available`. `total` is received batches minus consumed/disposed plus returns; `available` subtracts active reservations/requests so it reflects what can be allocated now.
- **Name:** Item display name. Click to select a row; double-click to edit.
- **Size / Brand / Other Specifications:** Free-form values entered when adding/editing the item.
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
- **Supplier / Size / Brand:** Select suppliers from existing entries; sizes and brands are free-form text.
- **PO Number:** Optional purchase order number.
- **Batch Quantity (Add only):** Number of units/batches to record for a new item. Must be a positive integer. Defaults to 1.
- **Other Specifications:** Free-form text for details (materials, model numbers, notes).
- **Acquisition Date:** Defaults to today; you may change it. **Changing this date recalculates expiration/calibration dates** based on the category thresholds.
- **Item Type:** Automatically set by category selection (Consumable or Non-Consumable). You can override this manually if needed. This toggles the meaning of the date fields:
  - If **Consumable**, the bottom-right date is **Expiration Date** (special value `No Expiration` allowed).
  - If **Non-Consumable**, the top-right date becomes **Disposal Date** and the bottom-right becomes **Calibration Date** (each can be left unset / special value to indicate None).
- **Editor Name/Initials (required):** You must supply this for audit purposes when saving or deleting.

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

- Saving will show warnings for missing required fields (item name, editor name) and for invalid batch quantities.
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
- Category and Supplier filters are exact matches based on names returned from the database.

## **How available stock is calculated (brief, factual)**

- `Total Stock` is computed from received batches minus consumed and disposed movements plus returns.
- `Available Stock` subtracts active reservations/requests so it reflects what can actually be allocated now.

## **Common tasks / quick recipes**

- **Add a new item:** Click **➕ Add Item**, fill the required fields (name, editor), set batch quantity and any dates, save.
- **Edit an item:** Select its row and click **✏️ Edit Item** or double-click the row, change fields, and save.
- **Delete an item:** Select row → **🗑️ Delete Item** → confirm, enter your name and reason → Delete.
- **Find items:** Use the **🔍 Search** box and the Category/Supplier filters together to narrow results.
- **Investigate an alert:** Sort or filter by dates, click the item, open edit dialog to view calibration/expiration/disposal fields and history.

## **Limitations & notes**

- The Inventory page is authoritative for item records and batches — use `Reports` for advanced exports and `Requisitions` for reservation history or to examine requests.
- The table display is optimized for readability; some long text fields (other specifications) may be truncated for layout reasons — open the item editor to see full text.
- If an operation fails (save/delete/refresh), an error dialog will appear. If that happens repeatedly, contact your administrator and include the action and time — the system logs provide further details.

-- End of Inventory Help --
