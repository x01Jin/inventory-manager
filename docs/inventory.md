# Inventory Page

Overview

- The Inventory page handles core item management. Items are stored in Items and Item_Batches and tracked with Stock_Movements.

Data Loading

- Data loads asynchronously in a background thread to prevent UI freezes
- A progress indicator displays during loading
- The table populates progressively as data becomes available
- Buttons are disabled during data load to prevent conflicts

## Importing items

A bulk import feature is available via the Inventory page. The importer accepts `.xlsx` files and supports flexible header matching (case- and space-insensitive) and will scan a few rows at the top of a sheet to find the header row if your file has title lines. Required fields are `name` (or `items` / `item name` variants), `stocks`, and `item type`. For details and rules (header examples, behavior on invalid rows) see `docs/importing_items.md`. Items without a specified category are assigned to "Uncategorized".

Inventory Table

- Columns include Stock/Available, Name, Category, Size, Brand, Supplier, Expiration Date, Calibration Date, Acquisition Date, Consumable, Last Modified, Alert Status.
- Supports sorting, searching and filtering with dynamic updates.

Item Management

- Add, edit and delete flows are available along with validation and audit tracking.
- **Categories are fixed** - see Settings documentation for the list of available categories and their thresholds.

## Adding Items with Auto-Calculated Dates

When adding a new item:

1. **Select a category**: The category determines the item type and date thresholds
2. **Item type is set automatically**: Consumable or Non-Consumable based on category
3. **Dates are pre-calculated** based on the acquisition date:
   - Consumables: Expiration date = acquisition date + category expiry months
   - Non-Consumables: Disposal date = acquisition date + category disposal years
   - Equipment: Calibration date = acquisition date + 1 year
4. **All dates remain editable** for manual adjustment if needed

Changing the category or acquisition date will recalculate the dates automatically.

Stock & Alerts

- Stock computations use Stock_Movements to produce on-hand counts. Movement types are standardized using the `MovementType` enum and enforced by a `CHECK` constraint in the database schema. Visual alerts indicate expiration and calibration due through row background coloring.

- The inventory table uses row background colors to indicate items requiring attention. Overdue items (expired, disposal overdue, or calibration overdue) display a reddish pink background. Items with approaching deadlines (warnings) display a pale yellow background. For non-consumable items with multiple dates, the most critical status determines the row color.

- **Items with 0 current stock are excluded from alerts and indicators**: When items reach 0 stock (fully depleted/disposed), they remain in the database for historical record and requisition integrity, but are excluded from expiration alerts, calibration alerts, and low stock warnings. This prevents alerts on items that are already depleted or disposed of.

- Data integrity: database-level triggers prevent stock movements that would make the available quantity for a batch or an item negative. The application performs validation and uses transactions to avoid oversubscription, but these triggers provide a defensive constraint at the database level.

## Alert Thresholds

Alert thresholds vary by item category and type:

| Category | Alert Type | Warning Threshold | Overdue When |
| -------- | ---------- | ----------------- | ------------ |
| Chemicals-Solid | Expiration | 180 days (6 months) before | Already expired |
| Chemicals-Liquid | Expiration | 180 days (6 months) before | Already expired |
| Prepared Slides | Expiration | 180 days (6 months) before | Already expired |
| Consumables | Expiration | 180 days (6 months) before | Already expired |
| Equipment | Disposal | 90 days (3 months) before | Already past disposal date |
| Equipment | Calibration | 90 days (3 months) before | Already past calibration date |
| Apparatus | Disposal | 90 days (3 months) before | Already past disposal date |
| Lab Models | Disposal | 90 days (3 months) before | Already past disposal date |
| Others | Disposal | 90 days (3 months) before | Already past disposal date |

**Calibration Details:**

- Initial calibration due 1 year from acquisition date
- Subsequent calibrations due 1 year from last calibration date
- Only equipment items have calibration tracking

**Severity Classification:**

- **Critical**: Already past deadline or within 7 days
- **Warning**: Within threshold period (90-180 days depending on type)
- **Info**: More than threshold period away

Row Background Colors:

- **Red/Pink**: Overdue (past deadline) - critical
- **Yellow**: Warning (within threshold) - needs attention
- **Default**: No immediate attention needed

## Stock Calculation Logic

Stock levels are calculated differently based on item type:

- **Consumables**: `Current Stock = Original Stock - Consumed - Disposed + Returned`
  - When consumables are used, the quantity is permanently deducted from stock
  
- **Non-consumables**: `Current Stock = Original Stock`
  - Non-consumables are returned after use, so original stock is retained
  - Items are tracked but the count does not decrease from usage

## Standard Categories

Items should be classified into the following standard categories:

- Equipment
- Apparatus
- Lab Models
- Chemicals-Solid
- Chemicals-Liquid
- Prepared Slides
- Consumables
- Others
