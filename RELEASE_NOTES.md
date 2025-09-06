# v2025.09.06

**Release Date:** September 06, 2025

## Summary

- **3** commits
- **72** files changed
- **17,992** insertions (+)
- **0** deletions (-)

## Features

- **Implement comprehensive release notes generation system** (55f972c)
  *Author: copilot-swe-agent[bot]*

- **Add activity logging for requester CRUD operations** (eb329de)
  - Replace old activity_logger in model with new manager
  - Add editor name input dialog for deletions in GUI
  - Create requesters_activity.py service module for centralized activity handling
  *Author: Jin*

## Other Changes

- **Initial plan** (9660cf2)
  *Author: copilot-swe-agent[bot]*

## Detailed Changes

### Files Modified

- `.gitignore`
- `COMPREHENSIVE_RELEASE_NOTES.md`
- `RELEASE_NOTES.json`
- `RELEASE_NOTES.md`
- `RELEASE_NOTES_README.md`
- `generate_release_notes.py`
- `inventory_app/database/connection.py`
- `inventory_app/database/models.py`
- `inventory_app/database/schema.sql`
- `inventory_app/gui/dashboard/__init__.py`
- `inventory_app/gui/dashboard/activity.py`
- `inventory_app/gui/dashboard/alerts.py`
- `inventory_app/gui/dashboard/dashboard_page.py`
- `inventory_app/gui/dashboard/metrics.py`
- `inventory_app/gui/dashboard/schedule_chart.py`
- `inventory_app/gui/inventory/__init__.py`
- `inventory_app/gui/inventory/alert_system.py`
- `inventory_app/gui/inventory/inventory_controller.py`
- `inventory_app/gui/inventory/inventory_filters.py`
- `inventory_app/gui/inventory/inventory_model.py`
- `inventory_app/gui/inventory/inventory_page.py`
- `inventory_app/gui/inventory/inventory_stats.py`
- `inventory_app/gui/inventory/inventory_table.py`
- `inventory_app/gui/inventory/item_editor.py`
- `inventory_app/gui/main_window.py`
- `inventory_app/gui/navigation.py`
- `inventory_app/gui/reports/__init__.py`
- `inventory_app/gui/reports/query_builder.py`
- `inventory_app/gui/reports/report_config.py`
- `inventory_app/gui/reports/report_generator.py`
- `inventory_app/gui/reports/report_utils.py`
- `inventory_app/gui/reports/report_worker.py`
- `inventory_app/gui/reports/reports_page.py`
- `inventory_app/gui/reports/ui_components.py`
- `inventory_app/gui/requesters/__init__.py`
- `inventory_app/gui/requesters/requester_editor.py`
- `inventory_app/gui/requesters/requester_model.py`
- `inventory_app/gui/requesters/requester_selector.py`
- `inventory_app/gui/requesters/requester_table.py`
- `inventory_app/gui/requesters/requesters_page.py`
- `inventory_app/gui/requisitions/__init__.py`
- `inventory_app/gui/requisitions/requisition_management/__init__.py`
- `inventory_app/gui/requisitions/requisition_management/base_requisition_dialog.py`
- `inventory_app/gui/requisitions/requisition_management/edit_requisition.py`
- `inventory_app/gui/requisitions/requisition_management/item_return_dialog.py`
- `inventory_app/gui/requisitions/requisition_management/item_selection_manager.py`
- `inventory_app/gui/requisitions/requisition_management/new_requisition.py`
- `inventory_app/gui/requisitions/requisition_management/requisition_validator.py`
- `inventory_app/gui/requisitions/requisition_management/return_processor.py`
- `inventory_app/gui/requisitions/requisition_preview.py`
- `inventory_app/gui/requisitions/requisitions_controller.py`
- `inventory_app/gui/requisitions/requisitions_filters.py`
- `inventory_app/gui/requisitions/requisitions_model.py`
- `inventory_app/gui/requisitions/requisitions_page.py`
- `inventory_app/gui/requisitions/requisitions_table.py`
- `inventory_app/gui/settings/settings_page.py`
- `inventory_app/gui/styles.py`
- `inventory_app/gui/widgets/date_selector.py`
- `inventory_app/main.py`
- `inventory_app/services/__init__.py`
- `inventory_app/services/alert_engine.py`
- `inventory_app/services/item_service.py`
- `inventory_app/services/requesters_activity.py`
- `inventory_app/services/requisition_activity.py`
- `inventory_app/services/stock_movement_service.py`
- `inventory_app/services/validation_service.py`
- `inventory_app/utils/activity_logger.py`
- `inventory_app/utils/date_utils.py`
- `inventory_app/utils/internal_time.py`
- `inventory_app/utils/logger.py`
- `release_notes_generator.py`
- `requirements.txt`
