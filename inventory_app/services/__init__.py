"""
Services package for inventory management application.
Provides composable services for business logic operations.
"""

from .item_service import ItemService
from .stock_movement_service import StockMovementService
from .validation_service import ValidationService
from .stock_calculation_service import (
    StockCalculationService,
    stock_calculation_service,
)
from .summary_tables import (
    SummaryTablesService,
    summary_tables_service,
    StockSummary,
    RequisitionSummary,
    StatisticsAggregate,
)
from .requisition_activity import (
    RequisitionActivityManager,
    requisition_activity_manager,
)

__all__ = [
    "ItemService",
    "StockMovementService",
    "ValidationService",
    "StockCalculationService",
    "stock_calculation_service",
    "SummaryTablesService",
    "summary_tables_service",
    "StockSummary",
    "RequisitionSummary",
    "StatisticsAggregate",
    "RequisitionActivityManager",
    "requisition_activity_manager",
]
