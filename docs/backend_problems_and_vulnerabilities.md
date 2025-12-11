# Backend Problems & Vulnerabilities

This document summarizes problems and vulnerabilities found in the backend of the Laboratory Inventory Monitoring System. Each item includes: description, impact, evidence (file references), severity, and recommended remediation.

---

How to read this document

- Severity: Critical > High > Medium > Low
- Evidence links point to the file and representative location in the repository for context.

---

## Critical

- **Unreliable last-insert ID handling**
  - Description: `SELECT last_insert_rowid()` is called on a separate connection instead of using the connection that performed the INSERT. This makes ID retrieval unreliable.
  - Impact: `id` values may be missing/wrong when creating dependent records (e.g., inserted `Categories`, `Items`, or `Requisitions` may not be properly linked), causing inconsistent DB state and logic failures.
  - Evidence: `inventory_app/database/connection.py` (execute_update / get_last_insert_id) and uses in models like `Category.save()` [inventory_app/database/connection.py](inventory_app/database/connection.py#L115-L160), [inventory_app/database/models.py](inventory_app/database/models.py#L10-L36)
  - Severity: Critical
  - Remediation: Change `execute_update()` to reliably return `cursor.lastrowid` for INSERTs; remove dependence on cross-connection `get_last_insert_id()` calls and update model `save()` implementations to use returned last id.
    - Status: **Completed** — `execute_update(..., return_last_id=True)` now returns `cursor.lastrowid`; model `save()` methods were refactored to use the returned ID and fallbacks to `get_last_insert_id()` were removed. Unit tests were added to validate the behavior.

- **Lack of atomic transactions for multi-step operations**
  - Description: Multi-step operations (create requisition + items + stock movements, item save + batch creation, multi-table deletes) are implemented as separate DB calls that each commit independently.
  - Impact: Partial completion on failure leaves the database inconsistent (e.g., a requisition created with missing items or stock movements), potentially requiring manual repair.
  - Evidence: `NewRequisitionDialog.create_requisition()` (separate saves and then movement creation) and `Item.save()` creating batches separately [inventory_app/gui/requisitions/requisition_management/new_requisition.py](inventory_app/gui/requisitions/requisition_management/new_requisition.py#L150-L240), [inventory_app/database/models.py](inventory_app/database/models.py#L279-L324)
  - Severity: Critical
  - Remediation: Add a `transaction()` context manager to `DatabaseConnection` and refactor multi-step flows to run inside a single transaction with proper rollback on error.

- **No concurrency control around stock reservations (race conditions)**
  - Description: Creation of reservation/consumption `Stock_Movements` is done without re-checking availability inside a transaction or applying locks.
  - Impact: Concurrent bookings can oversubscribe inventory leading to negative or incorrect available stock.
  - Evidence: `ItemSelectionManager.create_stock_movements_for_requisition()` inserts movements without transactional revalidation [inventory_app/gui/requisitions/requisition_management/item_selection_manager.py](inventory_app/gui/requisitions/requisition_management/item_selection_manager.py#L180-L240)
  - Severity: Critical
  - Remediation: Use transactions with SELECT ... FOR UPDATE semantics (or SQLite `BEGIN IMMEDIATE`) to re-check and reserve stock atomically; reject requests when insufficient stock.

---

## High

- **SQL built with inline string interpolation (injection & safety risk)**
  - Description: Report query builder embeds date values and builds dynamic CASE/column SQL with direct string formatting (f-strings), including period keys.
  - Impact: Risk of SQL injection or broken queries if any external input finds its way into those strings. Also harder to maintain and test.
  - Evidence: `ReportQueryBuilder` uses f-strings for date ranges and dynamic period columns [inventory_app/gui/reports/query_builder.py](inventory_app/gui/reports/query_builder.py#L100-L140)
  - Severity: High
  - Remediation: Use parameterized queries for date bounds and build dynamic columns safely (e.g., validate and escape period keys or use temporary tables / parameterized aggregates).

- **Inconsistent stock movement types & lack of enforcement**
  - Description: Movement types vary across code (`CONSUMPTION`, `RESERVATION`, `RETURN`, `DISPOSAL`, `REQUEST`, `LOST`) and not enforced by DB schema.
  - Impact: Logic relying on specific strings may misbehave, causing incorrect stock calculations and reporting.
  - Evidence: `stock_movement_service.py` and `item_service.py` reference multiple types inconsistently [inventory_app/services/stock_movement_service.py](inventory_app/services/stock_movement_service.py#L1-L60), [inventory_app/services/item_service.py](inventory_app/services/item_service.py#L1-L120)
  - Severity: High
  - Remediation: Introduce a single source-of-truth enum for movement types in code and add a DB CHECK constraint limiting allowed values in `Stock_Movements`.

- **Deletion logic relies on timing delays (time.sleep)**
  - Description: `Item.delete()` performs a deletion sequence with `time.sleep(0.1)` between deletes to "prevent constraint timing issues" rather than relying on correct FK constraints and transactions.
  - Impact: Fragile; can fail under load/concurrency and indicates schema or transaction design problems.
  - Evidence: `inventory_app/database/models.py` uses sequential deletes with `time.sleep` [inventory_app/database/models.py](inventory_app/database/models.py#L400-L480)
  - Severity: High
  - Remediation: Use `ON DELETE CASCADE` where appropriate or perform deletions within a single transaction and trust FK constraints; remove `sleep()` calls.

---

## Medium

- **Minimal input validation and sanitization**
  - Description: `ValidationService` performs basic presence checks but lacks strong type bounds (e.g., upper limits on quantities, proper server-side checks).
  - Impact: Malformed or malicious input could corrupt state or produce errors down the line.
  - Evidence: `inventory_app/services/validation_service.py` [inventory_app/services/validation_service.py](inventory_app/services/validation_service.py#L1-L140)
  - Severity: Medium
  - Remediation: Add stricter server-side validation (quantity upper bounds, date validations), centralize validation into service layer used by UI and programmatic APIs.

- **Activity log maintenance uses non-parameterized query & potentially inefficient approach**
  - Description: `cleanup_old_activities()` and `maintain_activity_limit()` construct queries with `.format()` and `DELETE ... WHERE id NOT IN (SELECT id ...)`.
  - Impact: Risk of malformed SQL and heavy operations on large `Activity_Log` table; should use parameterized statements and more efficient deletes.
  - Evidence: `inventory_app/utils/activity_logger.py` [inventory_app/utils/activity_logger.py](inventory_app/utils/activity_logger.py#L120-L180)
  - Severity: Medium
  - Remediation: Use parameterized queries and more efficient maintenance (e.g., delete by timestamp range or use a rolling table approach).

- **Missing index for lookups by `source_id` (performance)**
  - Description: `Stock_Movements.source_id` is used in delete/lookup operations (e.g., deleting all movements for a requisition), but no dedicated index exists for `source_id`.
  - Impact: Large deletion/lookup operations on `Stock_Movements` could be slow as DB grows.
  - Evidence: Schema defines `idx_movements_item_date` but not an index on `source_id` [inventory_app/database/schema.sql](inventory_app/database/schema.sql#L60-L84)
  - Severity: Medium
  - Remediation: Add an index on `Stock_Movements(source_id)` to improve common queries and deletes tied to requisitions.

- **Report query builder may produce very large or inefficient SQL**
  - Description: The dynamic generation of many CASE columns can create wide queries that are heavy to compute and may cause performance issues for large date ranges.
  - Impact: Slow report generation and memory pressure for big ranges.
  - Evidence: `ReportQueryBuilder._build_optimized_period_columns()` builds a CASE column per period key [inventory_app/gui/reports/query_builder.py](inventory_app/gui/reports/query_builder.py#L1-L200)
  - Severity: Medium
  - Remediation: Consider pre-aggregated summary tables, limit date range, or generate period aggregates in multiple queries.

---

## Low

- **Logging storing potentially sensitive notes/unstructured text**
  - Description: The `LimitedFileHandler` truncates by lines but logs may contain notes and editor user-supplied strings.
  - Impact: Sensitive info may be retained in logs in plaintext and accessible on file system.
  - Evidence: `inventory_app/utils/logger.py` [inventory_app/utils/logger.py](inventory_app/utils/logger.py#L1-L120)
  - Severity: Low
  - Remediation: Avoid logging PII or long free-form notes; use structured logs and consider rotating via `RotatingFileHandler` with size-based rotation and secure permissions.

- **Cron-style cleanup is application-driven rather than DB-managed**
  - Description: Activity cleanup is done from the app; if the app isn't run, cleanup won't happen.
  - Impact: Potential DB bloat if the app isn't run frequently.
  - Evidence: `activity_logger.cleanup_old_activities()` [inventory_app/utils/activity_logger.py](inventory_app/utils/activity_logger.py#L120-L140)
  - Severity: Low
  - Remediation: Allow DB-level retention policies or provide a scheduled job (cron/task) to run maintenance.

- **Some date parsing code can raise warnings and falls back silently**
  - Description: Several places parse isoformat strings with try/except and default to 'now' which may mask data issues.
  - Impact: Harder to detect malformed inputs upstream; debugging is more difficult.
  - Evidence: `models.Requisition.get_all()` uses try/except around datetime.fromisoformat [inventory_app/database/models.py](inventory_app/database/models.py#L640-L672)
  - Severity: Low
  - Remediation: Prefer validating and surfacing bad data to the caller or logging clearly when a parse fails.

## Not really a problem

these are actual reasonable problems for this system but are not really a problem or priority based on the stake holders' use case

- **No user authentication / weak identity model**
  - Description: `editor_name` is captured via a simple dialog (free text) and written to logs/history without authenticated user identity.
  - Impact: Audit trails are weak; user impersonation is trivial; limited ability to enforce role-based permissions.
  - Evidence: Editor name usage in return dialogs and activity logging [inventory_app/gui/requisitions/requisition_management/item_return_dialog.py](inventory_app/gui/requisitions/requisition_management/item_return_dialog.py#L372-L392)
  - Severity: High
  - Remediation: Add a `Users` table and authentication flow, require login and record user IDs for audit events; consider RBAC for sensitive actions.

---

## Suggested Prioritized Work Plan (short)

1. Fix last-insert ID behavior (Critical) — ensures basic correctness of inserts.
2. Add transaction support & convert critical flows to atomic transactions (Critical).
3. Add concurrency controls to stock reservation flow (Critical).
4. Parameterize queries and remove direct SQL interpolation (High).
5. Standardize and enforce movement type enum in schema and code (High).
6. Replace deletion `sleep()` hacks with transactional deletes and/or `ON DELETE CASCADE` (High).
7. Add authentication and audited user identity (High).
8. Add tests for critical flows (Medium) and add missing DB indexes where needed (Medium).

---

## Next steps

- I can implement the highest-priority fixes (start with `execute_update`/`get_last_insert_id` and adding a `transaction()` context manager) and add unit tests demonstrating correctness. Let me know if you want me to proceed and which item to start with.

---

*Generated during a code audit of the repository.*
