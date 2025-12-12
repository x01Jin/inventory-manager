# Reports

Overview

- Reports support Usage, Inventory, and (future) Requisition analytics. Exports are generated as Excel files using `openpyxl`.

Features

- Preset date ranges and custom ranges, automatic granularity selection for usage reports, and background processing to avoid UI blocking. The report engine uses `MovementType` to categorize movements and parameterized queries to prevent injection while building dynamic report columns.

Common Reports

- Stock Levels, Expiration, Low Stock Alerts, Acquisition History, and Calibration Due.
