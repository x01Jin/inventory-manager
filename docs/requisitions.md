# Requisitions

Overview

- Requisitions manage reservations and usage with lifecycle support: requested → active → returned / overdue.

Key Components

- Requisition table, detailed preview panel, and dialogs for new, edit and return processing.

Workflow

- Create requisitions with requester selection and item selection. The system performs stock validation and reservations. Requisitions creation uses `DatabaseConnection.transaction()` with an IMMEDIATE transaction to re-check and reserve stock atomically to prevent oversubscription. Concurrent reservation attempts will be rejected when stock is insufficient.

- Returns and partial returns supported with logging of consumed or lost items.

- Filtering and status: the requisitions UI supports filtering by status and the dashboard/statistics include requested requisitions in their summaries.

- Returns UX: return flows present clear summaries, confirmation prompts, and validation to reduce errors during return processing. Returned requisitions are rendered using a consistent theme color to make returned status easy to identify in lists and previews.

Validation & Audit

- Every modification requires an editor name and is recorded in history tables to preserve audit trails.
