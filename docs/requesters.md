# Requesters

Overview

- The Requesters page manages personnel who may request inventory. It supports typical CRUD operations and integration in requisition creation.

Data Loading

- Data loads asynchronously in a background thread to prevent UI freezes
- A progress indicator displays during loading
- The table populates progressively as data becomes available
- Buttons are disabled during data load to prevent conflicts

Key Components

- Requesters table with columns: Requisitions Count, Name, Affiliation, Group, Grade Level, Section, Created.

## Requester Fields

- **Name**: The name of the requester (e.g., teacher or student name)
- **Affiliation**: The requester's general affiliation (e.g., "Teacher", "Student")
- **Group Name**: The class or group identifier
- **Grade Level**: The grade level (e.g., "Grade 7", "Grade 8", "Grade 9", "Grade 10") - used for usage tracking by grade
- **Section**: The section name (e.g., "Section A", "Einstein") - used for usage tracking by section

Grade level and section information is used to generate reports showing usage broken down by grade and section per laboratory activity.

Validation

- Prevents deletion of requesters with active requisitions. All edits are logged with editor name for auditing.
