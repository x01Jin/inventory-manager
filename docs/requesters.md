# Requesters

Overview

- The Requesters page manages personnel who may request inventory. It supports typical CRUD operations and integration in requisition creation.

Key Components

- Requesters table with columns: Requisitions Count, Name, Affiliation, Group, Created.

Validation

- Prevents deletion of requesters with active requisitions. All edits are logged with editor name for auditing.
