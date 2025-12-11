# Dashboard

Overview

- The Dashboard is the application's central hub with multiple panels for quick insights: metrics, recent activity, schedule chart, and critical alerts.

Key Metrics

- Total Items, Total Stock, Recent Adds, Low Stock, Expiring Soon, Ongoing Reqs, Requested Reqs, Active Reqs, Overdue Reqs.

Activity

- Latest single activity and an activity history table. Useful for audit and operational review.

Alerts & Schedules

- Real-time alerts for expirations or low stock, and schedule overviews for activities that involve inventory.

Notes

- Dashboard automatically polls the service layer using dedicated managers; refresh logic is centralized in the alert and activity services.
