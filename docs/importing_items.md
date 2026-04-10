# Importing Inventory Items ✅

This document describes the Excel import feature for adding inventory items in bulk and explains how the importer parses, validates, and saves rows.

## Quick summary

- File: Excel (.xlsx)
- Minimum required columns: **name**, **stocks**, **item type** (accepts many human variants; header matching is case- and space-insensitive)
- Optional columns: **category**, **size**, **brand**, **supplier**, **other specifications**, **po number**, **expiration date**, **calibration date**, **acquisition date**
- Pre-import review: consumable rows with decimal `stocks` and no unit (example: `1.5`) are listed so you can choose a unit (`ml`, `L`, `mg`, `g`, `kg`) or skip each row.

---

## Import Process

The import runs in a background thread to prevent UI freezing during large imports:

1. Select an Excel file (.xlsx)
2. Enter editor name for audit trail
3. Click Import - the operation runs in the background
4. If decimal consumable stocks have missing units, a resolution dialog appears before import starts.
5. A progress bar displays real-time status: `[current/total], skipped: X`
6. A completion message shows total imported and skipped counts

The import can be cancelled while in progress by clicking the Cancel button.

---

## Header detection & normalization 🔎

- The importer scans the first 40 rows of the active worksheet to *find the header row* — this lets you include a top title block (report title, notes, etc.) above the table and still import the data.
- Header matching is **case-insensitive** and **space/underscore-insensitive**. For example, the following headers are all accepted and treated equivalently:
  - `Item Name`, `itemname`, `names`, `ITEMS` → mapped to `name`
  - `stocks`, `Stock` → mapped to `stocks`
  - `item type`, `item_type`, `type` → mapped to `item type`
- If the importer cannot find a header row containing the required groups (name + stocks + item type) within the scan window, import fails with a clear message telling you which required columns are missing.

## Accepted header variants (examples)

- Name: `name`, `item`, `items`, `item name`, `names` (and other variant spellings that normalize to the same key)
- Stocks: `stocks`, `stock`
- Item type: `item type`, `item_type`, `type`

---

## Row parsing rules & defaults 🧾

- **Name**: Required — rows with missing or empty names are skipped and reported.
- **Stocks**: The importer accepts a variety of free-form `stocks` values. Parsing rules are:
  - **Missing-unit review for consumables**: before import runs, rows classified as consumable that have decimal numeric stocks with no explicit unit (for example, `1.5`) are flagged for manual resolution. You can either:
    - choose a unit from the dropdown (`ml`, `L`, `mg`, `g`, `kg`) so import rewrites the stock value as `<value> <unit>` (example: `1.5` + `L` -> `1.5 L` -> quantity `1500`), or
    - skip that row.
  - **Numeric counts** (e.g., `2`, `10`) are parsed as integer quantities (floats coerced to int).
  - **Size-bearing entries** containing volume/mass units (e.g., `900ml`, `1.1 L`, `2 liters`, `125 g`, `500ml`) are treated as **usable quantity with size**: the importer records the matched `size` and calculates an integer usable quantity.
  - For larger units, the importer converts to base usable units so partial requisitions remain possible with integer quantities: `L/liter/litre/ltr/lt/lts` are converted to ml (`1 L -> 1000`), `gal/galon/gallon` forms follow the same project conversion (`1.1 gal -> 1100`), and `kg/kilo/kilogram` forms are converted to grams (`1 kilo -> 1000`). Units already in smaller forms like `ml` and `g` keep their numeric quantity.

  - **Supported size units** include common volume/mass units such as: `ml`, `milliliter`, `milliliters`, `millilitre`, `millilitres`, `l`, `lt`, `lts`, `g`, `gm`, `gms`, `gram`, `grams`, `kg`, `kilo`, `kilos`, `kilogram`, `kilograms`, `mg`, `milligram`, `milligrams`, `gal`, `galon`, `gallon`, `liter`, `liters`, `litre`, `litres`, and `ltr` (case-insensitive). The importer preserves the matched substring so the resulting `size` field closely resembles the input text.

  - **Package counts with piece details** (e.g., `1 box (100pcs)`, `2 packs of 50 pcs`) are converted to usable stock units using `packages * pieces` (so `1 box (100pcs)` becomes quantity `100`). Piece details are still recorded as notes and appended to `other_specifications`.
  - **Other leading counts with extra info** (e.g., `10 boxes`, `1 set of 8 pieces`) use the leading integer as the quantity; parenthetical or "of N pieces" style details are recorded as notes and appended to `other_specifications`.
  - **Empty / missing** stocks values result in `quantity = 0`.
  - **Invalid values** (no parseable number or recognized size) cause the row to be skipped and an explanatory message is included in the import log.
  - **Case & spacing**: size units are matched case-insensitively. They are space-sensitive except when attached to a number (both `900ml` and `900 ml` are accepted).

Notes

- The importer uses `inventory_app.utils.stock_parser.parse_stock_value` for parsing logic and is covered by unit tests (see `tests/backend/test_importing.py`).
- **Item type**: The importer normalizes and cleans the `item type` cell before classification:
  - Leading vendor prefixes like `TA,` are stripped when present (case-insensitive).
  - Values containing `consum`, `consumable`, `consumables`, `reagent`, `reagents`, or `chemical` are treated as **Consumable**.
  - Values containing `non` or `not` together with `consum` (e.g., `non consumable`, `TA, non consumable`) are treated as **Non-Consumable**. When ambiguous, the importer conservatively defaults to **Non-Consumable**.
  - The normalized result is stored in `Items.item_type` as a display value (`Consumable`, `Non-consumable`, or `TA, non-consumable`) and also mapped to `is_consumable` for stock behavior.
- **Supplier**: When a supplier name is provided, the importer resolves it to `Suppliers.id` case-insensitively. If it does not exist yet, the supplier is created automatically and linked to the item.
- **Text fields** (category, size, brand, supplier, other specifications, po number): If empty, they are stored as `N/A` (or left blank in the DB where appropriate). Note: if `stocks` contains a size and the explicit `size` column is empty the parsed size will be used instead.
- **Dates** (expiration, calibration, acquisition): Parsed to date objects when possible; unparseable or empty values become `None` (displayed as `N/A` in the UI).

---

### Stocks parsing examples

- `900ml` → quantity=900, size=`900ml`
- `1.1 L` → quantity=1100, size=`1.1 L`
- `1.1 gal` → quantity=1100, size=`1.1 gal`
- `2.5 L` → quantity=2500, size=`2.5 L`
- `1 kilo` → quantity=1000, size=`1 kilo`
- `125 gms` → quantity=125, size=`125 gms`
- `1 box (100pcs)` → quantity=100, notes=`(100pcs)` appended to `other_specifications`
- `2 packs of 50 pcs` → quantity=100, notes captured as `of 50 pcs`
- `1 set of 8 pieces` → quantity=1, notes captured as `of 8 pieces`

### Consumables rule (important)

- Requisition and return dialogs use integer quantities. To support partial-use consumables (for example, borrowing 100 out of 900 ml), ensure stocks represent usable units.
- If the `stocks` cell contains `900ml`, the importer converts it to `stocks = 900` and keeps `size = 900ml`.
- If the `stocks` cell contains `1 L`, the importer converts it to `stocks = 1000` and keeps `size = 1 L`.
- This allows users to request/return values like `100`, `250`, etc. instead of being limited to whole-container counts.

---

## Category handling 🗂️

Categories in the inventory system are fixed and read-only. When importing items:

- If the `category` column contains a value that matches an existing category (case-insensitive), that category is used.
- If the category value does not match any existing category, the item is assigned to the `Uncategorized` category.
- If the `category` column is empty or contains `N/A`, the item is assigned to the `Uncategorized` category.
- This approach ensures items always have a valid `category_id` and prevents foreign-key constraint failures.

**Note:** To use custom categories, they must be configured in the system before importing items.

---

## What the importer does on success ✅

- Creates a new `Item` record and an initial batch in `Item_Batches` whose `quantity_received` is the `stocks` value (one batch per imported row).
- Logs row-level success messages; the dialog shows a summary with the number of imported rows and any rows skipped along with reasons.

---

## Audit & logging 🧾

- The import dialog asks for an **Editor name** (used for audit records just like manual add/edit flows).
- The importer logs detailed debug information including the parameters used when attempting to save each item — these logs are useful for debugging errors such as FK constraint violations or parse failures.

---

## Error handling & messages ⚠️

- If the header row is missing required columns the import will abort and show a helpful error indicating the missing columns.
- Rows with invalid values (e.g., bad stock numbers, missing required fields) are skipped and included in the import log with an explanation.
- On unexpected DB errors the row is reported as failed; the importer continues processing subsequent rows where possible.

---

## Example header row (any of these variants will work)

```example
name | stocks | item type | category | size | brand | supplier | expiration date
```

---

## Notes & guidance 💡

- Use this tool for fast bulk creation of simple items and an initial batch. If you need advanced batch data (multiple batches per item, per-batch dates, or custom batch numbers), import minimal rows and then edit the items/batches with the UI or use the programmatic APIs.
- If an import fails repeatedly, share the **debug logs** (look for lines that show the save parameters and the error) and I can help diagnose the exact issue.
