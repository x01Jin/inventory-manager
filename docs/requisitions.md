# Requisitions

Overview

- Requisitions manage reservations and usage with lifecycle support: requested → active → returned / overdue.
- **Usage tracking is based on lab_activity_date** - the date when materials are actually used in the laboratory activity, NOT the borrow/request date.

Data Loading

- Data loads asynchronously in a background thread to prevent UI freezes
- A progress indicator displays during loading
- The table populates progressively as data becomes available
- Buttons are disabled during data load to prevent conflicts

Key Components

- Requisition table, detailed preview panel, and dialogs for new, edit and return processing.

Workflow

- Create requisitions with requester selection and item selection. The system performs stock validation and reservations. Requisitions creation uses `DatabaseConnection.transaction()` with an IMMEDIATE transaction to re-check and reserve stock atomically to prevent oversubscription. Concurrent reservation attempts will be rejected when stock is insufficient.

- Available items in requisition dialogs load asynchronously to keep the dialog responsive during item searches.

- Returns and partial returns supported with logging of consumed or lost items.

- Filtering and status: the requisitions UI supports filtering by status and the dashboard/statistics include requested requisitions in their summaries. Filters include search (by requester name, activity, items), requester dropdown, status dropdown, and date range.

- Returns UX: return flows present clear summaries, confirmation prompts, and validation to reduce errors during return processing. Returned requisitions are rendered using a consistent theme color to make returned status easy to identify in lists and previews.

Defective Items Tracking

- During return processing, non-consumable items can be marked as defective
- For each defective item, users specify:
  - Quantity defective (separate from lost count)
  - Condition type: BROKEN, DEFECTIVE, DAMAGED, or OTHER
  - Optional notes describing the defect
- Defective items are recorded to the `Defective_Items` table for reporting
- Defective Items Report available in Reports page

Print Functionality

- Requisitions can be exported to printable HTML format
- Click the "Print" button when a requisition is selected
- HTML report includes:
  - Requisition ID and status
  - Requester information
  - Timeline (expected request/return dates)
  - Activity details
  - Complete items list with quantities
  - Return details (for processed requisitions)
- Open the HTML file in a browser and use Ctrl+P to print

Validation & Audit

- Every modification requires an editor name and is recorded in history tables to preserve audit trails.
