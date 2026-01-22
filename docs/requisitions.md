# Requisitions

## Overview

- Requisitions manage reservations and usage with lifecycle support: requested → active → returned / overdue.
- **Usage tracking is based on lab_activity_date** - the date when materials are actually used in the laboratory activity, NOT the borrow/request date.

## Data Loading

- Data loads asynchronously in a background thread to prevent UI freezes
- A progress indicator displays during loading
- The table populates progressively as data becomes available
- Buttons are disabled during data load to prevent conflicts

## Key Components

- Requisition table, detailed preview panel, and dialogs for new, edit and return processing.

## Requester Selection

When creating a new requisition, you must select a registered requester:

1. Click **Select Requester** to open the requester selection dialog
2. Search for the requester by name, type, grade/section, or affiliation
3. Select the requester and click **Select**

The requester's type (Student, Teacher, or Faculty) is displayed along with their details.

### Requester Types and Validation

| Requester Type | Required for Requisition |
| --------------- | ------------------------- |
| Student | Grade Level and Section are used for activity details |
| Teacher | Department is shown in requester info |
| Faculty | Affiliation is shown in requester info |

## Workflow

- Create requisitions with requester selection and item selection. The system performs stock validation and reservations. Requisition creation uses `DatabaseConnection.transaction(immediate=True)` to re-check and reserve stock atomically (this uses an immediate transaction to prevent concurrent oversubscription). Stock availability and reservation logic relies on the centralized `stock_calculation_service` which implements the two-phase requested-quantity logic (active requisitions reduce available stock via REQUEST/RESERVATION movements; finalized requisitions do not). For performance, selection lists and expensive queries may be cached with `cached_query`; cache entries should be invalidated after writes using `db.invalidate_cache_for_table(...)` or `db.clear_query_cache()`.

- Available items in requisition dialogs load asynchronously to keep the dialog responsive during item searches.

- Returns and partial returns supported with logging of consumed or lost items.

- Filtering and status: the requisitions UI supports filtering by status and the dashboard/statistics include requested requisitions in their summaries. Filters include search (by requester name, activity, items), requester dropdown, status dropdown, and date range.

- Returns UX: return flows present clear summaries, confirmation prompts, and validation to reduce errors during return processing. Returned requisitions are rendered using a consistent theme color to make returned status easy to identify in lists and previews.

## Defective Items Tracking

- During return processing, non-consumable items can be marked as defective
- For each defective item, users specify:
  - Quantity defective (separate from lost count)
  - Required notes describing the defect
- Defective items are recorded to the `Defective_Items` table for reporting
- Defective Items Report available in Reports page

## Print Functionality

- Requisitions can be exported to printable HTML format
- Click the "Print" button when a requisition is selected
- HTML report includes:
  - Requisition ID and status
  - Requester information (name, type, and type-specific details)
  - Timeline (expected request/return dates)
  - Activity details
  - Complete items list with quantities
  - Return details (for processed requisitions)
- Open the HTML file in a browser and use Ctrl+P to print

## Validation & Audit

- Every modification requires an editor name and is recorded in history tables to preserve audit trails.
