# Known Limitations

This page lists limitations verified from the current codebase.
It is intentionally direct so planning work is easier.

## 1) Local SQLite Design Limits Multi-User Scaling

The app is desktop-first with a single SQLite file (`inventory.db`).

Effect:

- Good for local/small-team usage.
- Not ideal for high-concurrency, distributed, or server-based workflows without redesign.

## 2) No Built-In Authentication or Role Permissions

There is no dedicated auth or role-based permission layer in the current architecture.

Effect:

- Access control depends on machine/user environment, not app-level identities and permissions.

## 3) Individual Request Mode Still Depends on Core Requisition Fields

Schema comments mention individual request handling, but `Requisitions` still requires fields like `requester_id`, `lab_activity_name`, and `lab_activity_date`.

Effect:

- "Individual" requests still follow much of the standard requisition data contract.

## 4) Documentation Sources Are Split

In-app Help primarily loads markdown from `inventory_app/gui/help/*.md`, while MkDocs uses `docs/*.md`.

Effect:

- Content can drift if only one doc set is updated.

## Suggested Priority Order

1. Decide a single source of truth (or automated sync process) for user-facing docs.
2. Rework individual request data contract if activity fields should become optional in that mode.
3. Add app-level authentication/authorization if shared-device usage is expected.
4. Plan backend architecture changes for multi-user/server deployments.
