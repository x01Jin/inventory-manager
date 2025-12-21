# Requesters

Overview

- The Requesters page manages personnel who may request inventory. It supports typical CRUD operations and integration in requisition creation.

Data Loading

- Data loads asynchronously in a background thread to prevent UI freezes
- A progress indicator displays during loading
- The table populates progressively as data becomes available
- Buttons are disabled during data load to prevent conflicts

Key Components

- Requesters table with columns: Requisitions Count, Name, Affiliation, Group, Created.

Validation

- Prevents deletion of requesters with active requisitions. All edits are logged with editor name for auditing.
