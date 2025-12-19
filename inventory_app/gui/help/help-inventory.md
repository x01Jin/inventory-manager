# Inventory Help

The Inventory page is the primary place to view, search, and manage all items, batches, and stock information in the system. This help page describes every user-facing control, what the numbers mean, and how to perform the common tasks you will need.

## **Top controls (header)**

- **➕ Add Item:** Opens the Item Editor to add a new item and (for new items) an initial batch quantity. Required: Item name and Editor name/initials.
- **✏️ Edit Item:** Enabled when you select a row; opens the Item Editor to edit the selected item. You can also double-click a row to edit.
- **🗑️ Delete Item:** Enabled when you select a row; prompts for confirmation and requires your name/initials and a deletion reason. Deletions are permanent.
- **🔄 Refresh:** Reloads items, filters, and statistics from the database.
- **⬇️ Import Items:** Opens the Import dialog to import items from an `.xlsx` file. The importer scans the first 40 rows to locate the header row (so top title rows are ignored), and header names are matched case- and space-insensitively. Minimum required fields are `name` (or variants like `item` / `items`), `stocks`, and `item type`. Categories are auto-resolved (or created) to avoid FK errors. If the import fails, check the import log which lists skipped rows and reasons.

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
- **Calibration Date:** For non-consumables, shows last calibration date; color-coded if approaching or overdue.
- **Expiry/Disposal Date:** For consumables this is expiration; for non-consumables this is disposal date. Color-coded for warnings and expiries.
- **Item Type:** `Consumable` or `Non-Consumable` — affects which date is shown (expiration vs calibration/disposal).
- **Acquisition Date:** When the item or batch was acquired.
- **Last Modified:** Timestamp of the most recent change (format `MM/DD/YYYY HH:MM`).

Notes about sorting and selection:

- Click any column header to sort. The table applies sensible defaults: stock shows highest availability first, names sort A→Z, and date columns default to newest-first.
- Select a row to enable **Edit** and **Delete** buttons.

## **Color coding & alerts (what the colors mean)**

- **Expired / Overdue (red):** Item is past its expiration or disposal date, or calibration is overdue.
- **Expiring / Disposal approaching (yellow):** Disposal/expiration is approaching (short warning window).
- **Calibration Warning (orange):** Next calibration is approaching.
- **Default / OK (standard text color):** No immediate alert.

Alert thresholds (how statuses are derived):

- **Consumables:** Items with an expiration date <= 180 days (6 months) are flagged `Expiring`; dates already past are `Expired`.
- **Non-Consumables:** Calibration next-date within 90 days is `Cal. Warning`; overdue is `Cal. Overdue`. Disposal within 90 days is `Expiring`; already past disposal is `Expired`. When multiple alerts apply they are shown together (for example, `CAL_WARNING and EXPIRING`).

## **Item Editor (Add / Edit)**

Key fields and behaviors in the Add/Edit dialog:

- **Name (required):** The visible name of the item.
- **Category / Supplier / Size / Brand:** Select from existing entries; dropdowns are populated from the database.
- **PO Number:** Optional purchase order number.
- **Batch Quantity (Add only):** Number of units/batches to record for a new item. Must be a positive integer. Defaults to 1.
- **Other Specifications:** Free-form text for details (materials, model numbers, notes).
- **Acquisition Date:** Defaults to today; you may change it.
- **Item Type:** Choose `Consumable` or `Non-Consumable`. This toggles the meaning of the date fields:
  - If **Consumable**, the bottom-right date is **Expiration Date** (special value `No Expiration` allowed).
  - If **Non-Consumable**, the top-right date becomes **Disposal Date** and the bottom-right becomes **Calibration Date** (each can be left unset / special value to indicate None).
- **Editor Name/Initials (required):** You must supply this for audit purposes when saving or deleting.

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
