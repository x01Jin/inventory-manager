# Inventory Page

Overview

- The Inventory page handles core item management. Items are stored in Items and Item_Batches and tracked with Stock_Movements.

Data Loading

- Data loads asynchronously in a background thread to prevent UI freezes
- A progress indicator displays during loading
- The table populates progressively as data becomes available
- Buttons are disabled during data load to prevent conflicts

## Importing items

A bulk import feature is available via the Inventory page. The importer accepts `.xlsx` files and supports flexible header matching (case- and space-insensitive) and will scan a few rows at the top of a sheet to find the header row if your file has title lines. Required fields are `name` (or `items` / `item name` variants), `stocks`, and `item type`. For details and rules (category auto-creation, header examples, behavior on invalid rows) see `docs/importing_items.md`.

Inventory Table

- Columns include Stock/Available, Name, Category, Size, Brand, Supplier, Expiration Date, Calibration Date, Acquisition Date, Consumable, Last Modified, Alert Status.
- Supports sorting, searching and filtering with dynamic updates.

Item Management

- Add, edit and delete flows are available along with validation and audit tracking.

Stock & Alerts

- Stock computations use Stock_Movements to produce on-hand counts. Movement types are standardized using the `MovementType` enum and enforced by a `CHECK` constraint in the database schema. Visual alerts indicate expiration and calibration due through row background coloring.

- The inventory table uses row background colors to indicate items requiring attention. Overdue items (expired, disposal overdue, or calibration overdue) display a reddish pink background. Items with approaching deadlines (warnings) display a pale yellow background. For non-consumable items with multiple dates, the most critical status determines the row color.

- Data integrity: database-level triggers prevent stock movements that would make the available quantity for a batch or an item negative. The application performs validation and uses transactions to avoid oversubscription, but these triggers provide a defensive constraint at the database level.
