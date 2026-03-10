# Dashboard

Overview

- The Dashboard is the application's central hub providing real-time visibility into inventory status, requisition workflows, and critical alerts. It aggregates data from multiple services to present a unified operational view without requiring navigation to individual pages.

## Dashboard Panels

### Key Metrics Grid (3x3 Layout)

The dashboard displays nine metric cards providing instant insight into system state:

| Metric | Description | Calculation |
| ------- | ------------- | ------------- |
| **Total Items** | Count of distinct inventory items | `SELECT COUNT(*) FROM Items` |
| **Total Stock** | Aggregate quantity across all non-disposed batches | `SUM(quantity_received) - SUM(consumed) - SUM(disposed) + SUM(returned)` |
| **Recent Adds** | Items modified in the last 7 days | `COUNT(*) WHERE last_modified >= datetime('now', '-7 days')` |
| **Low Stock** | Items with stock between 1-9 | `COUNT(*) WHERE current_stock BETWEEN 1 AND 9` |
| **Expiring Soon** | Items currently in status `EXPIRING` | Derived from `item_status_service.get_alert_counts()['expiring']` |
| **Ongoing Reqs** | Requisitions in requested/active/overdue status | `COUNT(*) WHERE status IN ('requested', 'active', 'overdue')` |
| **Requested Reqs** | Requisitions awaiting fulfillment | `COUNT(*) WHERE status = 'requested'` |
| **Active Reqs** | Requisitions currently checked out | `COUNT(*) WHERE status = 'active'` |
| **Overdue Reqs** | Requisitions past expected return date | `COUNT(*) WHERE status = 'overdue' AND expected_return < now` |

**Notes:**

- Metrics are loaded asynchronously in background threads to prevent UI freezes
- Metrics use consolidated queries and shared status-service counts to keep dashboard panels consistent
- Loading state is displayed while metrics compute in the background
- Total Stock excludes disposed batches and accounts for consumptions, disposals, and returns
- Low Stock metric uses absolute threshold (1-9); percentage-based thresholds are used in reports only
- Expiring Soon metric and Critical Alerts now share the same status windows (consumables: 180 days, non-consumables: 90 days).

### Activity Panel

The Activity panel provides an audit trail of recent system events:

- **Latest Activity**: Single most recent activity with full description, user, and timestamp
- **Activity History**: Table showing recent activities (limited to ~20 entries by system policy)

**Activity Types Logged:**

- `ITEM_ADDED`, `ITEM_EDITED`, `ITEM_DELETED`
- `REQUISITION_CREATED`, `REQUISITION_RETURNED`, `REQUISITION_EDITED`, `REQUISITION_DELETED`
- `REQUESTER_ADDED`, `REQUESTER_EDITED`, `REQUESTER_DELETED`
- `STOCK_CONSUMED`, `STOCK_RETURNED`, `STOCK_RESERVED`, `STOCK_DISPOSED`
- `BATCH_CREATED`, `DEFECTIVE_ITEM_REPORTED`

**Retention Policy:**

- Activities older than 90 days are automatically deleted
- Maximum of 20 activities retained (oldest removed when limit exceeded)
- Managed by database triggers on the Activity_Log table

### Schedule Chart

The Schedule Chart displays upcoming requisitions for operational planning:

- **Data Source**: Requisitions with `expected_request >= now` and status in (`requested`, `active`, `overdue`)
- **Display Limit**: Shows up to 5 rows for compactness (upstream query fetches 7)
- **Columns**: Status badge, Requester name, Expected Request datetime, Expected Return datetime
- **Purpose**: Quick visibility into what's coming up and what needs to be returned

### Critical Alerts Panel

Real-time alerts for items requiring immediate attention:

**Alert Types:**

| Alert Type | Source | Threshold |
| ----------- | -------- | ----------- |
| **Expired** | Expiration/disposal/calibration date passed | Already past due → Critical |
| **Expiring Soon** | Consumable expiration | Within 180 days (6 months) |
| **Disposal Warning** | Non-consumable disposal | Within 90 days (3 months) |
| **Calibration Warning** | Equipment calibration | Within 90 days (3 months) |
| **Low Stock** | Percentage threshold | Consumables < 20%, Non-consumables < 10% |

**Severity Classification:**

- **Critical**: Already past deadline (days_until <= 0) or within 7 days
- **Warning**: Within 30 days (consumables) or 90 days (non-consumables/calibration)
- **Info**: More than 30 days away |

**Zero-Stock Exclusion:**

- Items with 0 current stock are excluded from all alerts
- This prevents alerts on fully consumed or disposed items
- Historical data remains available in disposal/update reports

**Display Rules:**

- Maximum 50 alert rows displayed (tooltip indicates additional alerts if exceeded)
- Critical alerts (overdue/expired) appear first
- Color-coded: Critical (red/pink), Warning (yellow), Info (default)
- Alerts are deduplicated by item

## Data Refresh Behavior

- Dashboard loads asynchronously when the page opens or when switching to the Dashboard tab
- Metrics, activity, and alerts load in parallel using background workers
- Loading state is shown on metric cards ("...") until data arrives
- Dashboard uses the WorkerPool with QThreadPool for background execution
- Query consolidation reduces database roundtrips versus per-card loading
- Workers can be cancelled to prevent stale data from overwriting fresh data

## Integration with Other Pages

- Click metrics to navigate to filtered views:
  - Low Stock → Inventory page with low-stock filter
  - Expiring Soon → Inventory page with date filter
  - Overdue Reqs → Requisitions page with overdue filter
- Activity entries link to related entities (click to open item/requisition)
- Alerts provide quick action links to affected items

## Dashboard Configuration

The dashboard is read-only and non-configurable. Data sources and thresholds are defined in:

- `inventory_app/gui/dashboard/metrics_worker.py` - Consolidated metrics queries and status-aligned expiring count
- `inventory_app/gui/dashboard/metrics.py` - Metric definitions and UI widgets
- `inventory_app/gui/dashboard/activity.py` - Activity loading and display
- `inventory_app/gui/dashboard/alerts.py` - Alert loading and display
- `inventory_app/services/alert_engine.py` - Alert generation logic
- `inventory_app/services/item_status_service.py` - Status computations
- `inventory_app/gui/dashboard/schedule_chart.py` - Schedule data fetching

## Limitations

- Dashboard provides overview only; detailed operations require navigation to specific pages
- No export functionality; use Reports page for exports
- Activity history is limited (~20 entries) by design for performance
- Alert display is capped at 50 rows for UI performance

## Performance Optimizations

The dashboard implements several performance optimizations:

1. **Async Loading**: All dashboard sections (metrics, activity, alerts) load asynchronously using QThreadPool workers
2. **Query Consolidation**: Metrics use 4 consolidated queries instead of 9+ separate database calls
3. **Cancellation Support**: Background workers can be cancelled to prevent stale data from overwriting fresh data on rapid refresh
4. **Parallel Loading**: Metrics, activity, and alerts load simultaneously rather than sequentially
