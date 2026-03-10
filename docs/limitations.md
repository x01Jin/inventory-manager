# Known Limitations

This page lists limitations verified from the current codebase.
It is intentionally direct so planning work is easier.

## 1) Migration Discovery Is Not Fully Wired

- `MigrationManager` is initialized with `__file__` from `migrations/__init__.py`.
- The discovery logic scans `self.migrations_dir.glob("[0-9]*.py")`.
- There are currently no numbered migration files in `inventory_app/database/migrations`.

Effect:

- Startup migration checks run, but no actual migration scripts are discovered/applied right now.

## 2) Reports Page Refresh Hook Is Miswired

In `inventory_app/gui/main_window.py`, page refresh handling for page index `4` checks `reports_page` but calls `help_page.load_current_tab()`.

Effect:

- Reports page refresh behavior is likely inconsistent with intended design.

## 3) Validation Field Names Do Not Match Current Requisition Naming

`inventory_app/services/validation_service.py` expects `date_requested` in requisition payload validation, while the schema and service layer use `expected_request` and `expected_return` naming.

Effect:

- If this validator is used in new flows without adaptation, valid requisition payloads may fail validation.

## 4) Local SQLite Design Limits Multi-User Scaling

The app is desktop-first with a single SQLite file (`inventory.db`).

Effect:

- Good for local/small-team usage.
- Not ideal for high-concurrency, distributed, or server-based workflows without redesign.

## 5) No Built-In Authentication or Role Permissions

There is no dedicated auth or role-based permission layer in the current architecture.

Effect:

- Access control depends on machine/user environment, not app-level identities and permissions.

## 6) Individual Request Mode Still Depends on Core Requisition Fields

Schema comments mention individual request handling, but `Requisitions` still requires fields like `requester_id`, `lab_activity_name`, and `lab_activity_date`.

Effect:

- "Individual" requests still follow much of the standard requisition data contract.

## 7) Documentation Sources Are Split

In-app Help primarily loads markdown from `inventory_app/gui/help/*.md`, while MkDocs uses `docs/*.md`.

Effect:

- Content can drift if only one doc set is updated.

## 8) Calibration Policy Is Implicit, Not Strictly Enforced by Category

Category config marks calibration as required for Equipment only, but status logic checks calibration dates for any non-consumable item when a calibration date exists.

Effect:

- Apparatus/Lab Models/Others can still enter calibration warning/overdue states if a calibration date is manually set.
- Behavior is valid technically but policy intent is ambiguous.

## 9) Disposal Rules Are Duplicated Across Modules

Category lifespan defaults are defined in `inventory_app/services/category_config.py`, while status evaluation in `inventory_app/services/item_status_service.py` also applies category-name heuristics.

Effect:

- Business rules can drift when one module changes and the other is not updated.
- Future category additions are higher risk without a single source of truth for lifecycle rules.

## 10) Legacy/Conflicting Comments Still Exist in Status Service

Some comments and constants in `inventory_app/services/item_status_service.py` still reference older wording (for example, mixed Glassware/Apparatus/Equipment phrasing).

Effect:

- Maintainers can misread current business rules while implementing changes.
- Documentation rewrites can regress if comments are treated as authoritative.

## 11) Dashboard Uses Different "Expiring Soon" Windows Across Panels

The dashboard metric card for `Expiring Soon` currently uses a 30-day cutoff (`metrics_worker.py`), while the Critical Alerts panel uses broader warning windows (180 days for consumables and 90 days for non-consumables/calibration).

Effect:

- Users can see different "expiring" counts on the same page.
- This behavior is now documented, but product intent is still ambiguous and can cause support confusion.

## Suggested Priority Order

1. Fix migration discovery and add real migration scripts.
2. Fix reports page refresh handler.
3. Align validation payload keys with requisition schema/service naming.
4. Unify category lifecycle/alert logic into one source of truth used by both editor defaults and status evaluation.
5. Clarify calibration policy for non-equipment categories and enforce it consistently in UI + status logic.
6. Decide whether dashboard expiring metrics should match alert windows or remain intentionally different (and standardize naming accordingly).
7. Decide a single source of truth (or sync process) for user-facing docs.
