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

- Create requisitions by selecting a requester and adding items. The system checks stock before saving and reserves quantities so the same stock is not double-allocated.

- Available items in requisition dialogs load asynchronously to keep the dialog responsive during item searches.

- Returns and partial returns supported with logging of consumed or lost items.

- Consumables are processed using integer usable quantities. For unit-based items, import stocks as usable units so partial borrowing/returning is possible (examples: `900ml` in import becomes stock `900`; `1 L` becomes stock `1000`).

- Filtering and status: the requisitions UI supports filtering by status and the dashboard/statistics include requested requisitions in their summaries. Filters include search (by requester name, activity, items), requester dropdown, status dropdown, and date range.

- Returns UX: return flows present clear summaries, confirmation prompts, and validation to reduce errors during return processing. Returned requisitions are rendered using a consistent theme color to make returned status easy to identify in lists and previews.

## Defective Items Tracking

- During return processing, non-consumable items can be marked as defective
- For each defective item, users specify:
  - Quantity defective (separate from lost count)
  - Required notes describing the defect
- Defective items are recorded to the `Defective_Items` table for reporting
- Inventory rows with defective records display a DEF badge in the Name column for quick visibility
- Clicking DEF opens item usage history with defective filtering enabled by default
- Item usage history always includes defective controls and filtering, even when opened by double-click
- Custodians can confirm quantities as `Disposed` or `Not Defective` with explicit quantity selection
- Current Stock subtracts unresolved defectives; `Disposed` confirmations subtract from Total Stock only
- Lifecycle alert colors remain primary for row highlighting; the defective badge is a secondary indicator
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
- Requisition updates now capture field-level audit values (`field_name`, `old_value`, `new_value`) in history records when changes are detected.
