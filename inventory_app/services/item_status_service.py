"""
Item status service for calculating item status based on expiration and calibration dates.
Handles status calculation for consumables and non-consumables with proper alert logic.

Policy source of truth:
- Category lifecycle and calibration applicability come from category_config.
- Status calculations consume those rules instead of duplicating category heuristics.
"""

from typing import Dict, List, Optional
from datetime import date, timedelta
from dataclasses import dataclass

from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.services.stock_calculation_service import stock_calculation_service
from inventory_app.services.category_config import get_category_config


# Alert threshold constants (in days)
CHEMICAL_EXPIRY_WARNING_DAYS = 180  # 6 months before expiration
NON_CONSUMABLE_WARNING_DAYS = 90  # 3 months before disposal target
CALIBRATION_WARNING_DAYS = 90  # 3 months before calibration due
CALIBRATION_INTERVAL_DAYS = 365  # Yearly calibration


@dataclass
class ItemStatus:
    """Represents the status of an inventory item."""

    item_id: int
    status: str  # 'OK', 'EXPIRING', 'EXPIRED', 'CAL_WARNING', 'CAL_DUE'
    days_until: Optional[int] = None
    reference_date: Optional[date] = None
    has_defective: bool = False
    defective_count: int = 0


class ItemStatusService:
    """
    Service for calculating item status based on expiration and calibration logic.
    Handles both consumables and non-consumables with appropriate alert periods.
    """

    # SQLite parameter limit (safety margin)
    SQLITE_PARAM_LIMIT = 900

    def __init__(self):
        """Initialize the item status service."""
        logger.info("Item status service initialized")

    def get_statuses_for_items(
        self, item_ids: List[int]
    ) -> Dict[int, Optional[ItemStatus]]:
        """
        Get status for multiple items in optimized batch queries.

        Handles SQLite's 999 parameter limit by chunking large ID lists.
        Transforms from O(N) queries to O(1) or O(chunk_count) queries.

        Args:
            item_ids: List of item IDs to fetch statuses for

        Returns:
            Dictionary mapping item_id to ItemStatus (or None if not found)
        """
        if not item_ids:
            return {}

        # Remove duplicates and None values
        unique_ids = list(set(id for id in item_ids if id is not None))
        if not unique_ids:
            return {}

        # Chunk IDs to respect SQLite parameter limit
        chunks = [
            unique_ids[i : i + self.SQLITE_PARAM_LIMIT]
            for i in range(0, len(unique_ids), self.SQLITE_PARAM_LIMIT)
        ]

        result: Dict[int, Optional[ItemStatus]] = {}

        try:
            # Execute for each chunk and merge results
            all_rows = []
            for chunk in chunks:
                query = """
                SELECT i.id, i.name, i.is_consumable, i.expiration_date, i.calibration_date,
                       i.acquisition_date, c.name as category_name,
                       COALESCE(dc.defective_count, 0) as defective_count
                FROM Items i
                LEFT JOIN Categories c ON i.category_id = c.id
                LEFT JOIN (
                    SELECT
                        current_defectives.item_id,
                        COALESCE(SUM(current_defectives.current_defective_qty), 0) AS defective_count
                    FROM (
                        SELECT
                            di.id,
                            di.item_id,
                            MAX(0,
                                di.quantity - COALESCE(SUM(
                                    CASE
                                        WHEN dia.action_type IN ('DISPOSED', 'NOT_DEFECTIVE')
                                        THEN dia.quantity
                                        ELSE 0
                                    END
                                ), 0)
                            ) AS current_defective_qty
                        FROM Defective_Items di
                        LEFT JOIN Defective_Item_Actions dia ON dia.defective_item_id = di.id
                        GROUP BY di.id, di.item_id, di.quantity
                    ) current_defectives
                    GROUP BY current_defectives.item_id
                ) dc ON i.id = dc.item_id
                WHERE i.id IN ({})
                """.format(",".join("?" * len(chunk)))
                rows = db.execute_query(query, tuple(chunk))
                all_rows.extend(rows)

            # Calculate status for each item
            for item_data in all_rows:
                status = self._calculate_status(item_data)
                if status:
                    result[status.item_id] = status

            logger.debug(
                f"Batch-fetched status for {len(result)} items (chunks: {len(chunks)})"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to batch-fetch statuses: {e}")
            # Fallback: return empty dict (caller will handle per-item)
            return {}

    def get_item_status(self, item_id: int) -> Optional[ItemStatus]:
        """
        Get the status for a specific item.

        Args:
            item_id: ID of the item

        Returns:
            ItemStatus object or None if item not found
        """
        try:
            # Get item data
            query = """
            SELECT i.id, i.name, i.is_consumable, i.expiration_date, i.calibration_date,
                     i.acquisition_date, c.name as category_name,
                     COALESCE(dc.defective_count, 0) as defective_count
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
                 LEFT JOIN (
                  SELECT
                      current_defectives.item_id,
                      COALESCE(SUM(current_defectives.current_defective_qty), 0) AS defective_count
                  FROM (
                      SELECT
                          di.id,
                          di.item_id,
                          MAX(0,
                              di.quantity - COALESCE(SUM(
                                  CASE
                                      WHEN dia.action_type IN ('DISPOSED', 'NOT_DEFECTIVE')
                                      THEN dia.quantity
                                      ELSE 0
                                  END
                              ), 0)
                          ) AS current_defective_qty
                      FROM Defective_Items di
                      LEFT JOIN Defective_Item_Actions dia ON dia.defective_item_id = di.id
                      GROUP BY di.id, di.item_id, di.quantity
                  ) current_defectives
                  GROUP BY current_defectives.item_id
                 ) dc ON i.id = dc.item_id
            WHERE i.id = ?
            """
            rows = db.execute_query(query, (item_id,))
            if not rows:
                return None

            item_data = rows[0]
            return self._calculate_status(item_data)

        except Exception as e:
            logger.error(f"Failed to get status for item {item_id}: {e}")
            return None

    def get_all_items_status(self) -> List[ItemStatus]:
        """
        Get status for all items in the inventory.
        Excludes items with 0 current stock to prevent alerts for depleted items.

        Returns:
            List of ItemStatus objects
        """
        try:
            query = stock_calculation_service.get_item_status_stock_subquery()
            stock_params = stock_calculation_service.get_item_status_stock_params()

            query = f"""
            SELECT i.id, i.name, i.is_consumable, i.expiration_date, i.calibration_date,
                   i.acquisition_date, c.name as category_name,
                   COALESCE(dc.defective_count, 0) as defective_count
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN (
                SELECT
                    current_defectives.item_id,
                    COALESCE(SUM(current_defectives.current_defective_qty), 0) AS defective_count
                FROM (
                    SELECT
                        di.id,
                        di.item_id,
                        MAX(0,
                            di.quantity - COALESCE(SUM(
                                CASE
                                    WHEN dia.action_type IN ('DISPOSED', 'NOT_DEFECTIVE')
                                    THEN dia.quantity
                                    ELSE 0
                                END
                            ), 0)
                        ) AS current_defective_qty
                    FROM Defective_Items di
                    LEFT JOIN Defective_Item_Actions dia ON dia.defective_item_id = di.id
                    GROUP BY di.id, di.item_id, di.quantity
                ) current_defectives
                GROUP BY current_defectives.item_id
            ) dc ON i.id = dc.item_id
            LEFT JOIN (
                {query}
            ) stock ON i.id = stock.item_id
            WHERE COALESCE(stock.total_stock, 0) > 0
            ORDER BY i.name
            """
            full_params = stock_params
            rows = db.execute_query(query, full_params)
            statuses = []

            for item_data in rows:
                status = self._calculate_status(item_data)
                if status:
                    statuses.append(status)

            logger.debug(
                f"Calculated status for {len(statuses)} items (excluding 0-stock items)"
            )
            return statuses

        except Exception as e:
            logger.error(f"Failed to get all items status: {e}")
            return []

    def get_items_by_status(self, status_filter: str) -> List[ItemStatus]:
        """
        Get items filtered by status.

        Args:
            status_filter: Status to filter by ('OK', 'EXPIRING', etc.)

        Returns:
            List of ItemStatus objects matching the filter
        """
        all_statuses = self.get_all_items_status()
        return [status for status in all_statuses if status.status == status_filter]

    def get_alert_counts(self) -> Dict[str, int]:
        """
        Get counts of items by status for dashboard display.
        Handles combined statuses like "CAL_WARNING and EXPIRING".

        Returns:
            Dictionary with status counts
        """
        all_statuses = self.get_all_items_status()
        counts = {
            "total": len(all_statuses),
            "ok": 0,
            "expiring": 0,
            "expired": 0,
            "calibration_warning": 0,
            "calibration_due": 0,
        }

        for status in all_statuses:
            if status.status == "OK":
                counts["ok"] += 1
            else:
                # Handle combined statuses by splitting on " and "
                status_parts = status.status.split(" and ")
                for status_part in status_parts:
                    status_part = status_part.strip()
                    if status_part == "EXPIRING":
                        counts["expiring"] += 1
                    elif status_part == "EXPIRED":
                        counts["expired"] += 1
                    elif status_part == "CAL_WARNING":
                        counts["calibration_warning"] += 1
                    elif status_part == "CAL_DUE":
                        counts["calibration_due"] += 1

        return counts

    def _calculate_status(self, item_data: Dict) -> Optional[ItemStatus]:
        """
        Calculate status for an item based on its data.

        Args:
            item_data: Dictionary containing item information

        Returns:
            ItemStatus object
        """
        try:
            item_id = item_data["id"]
            is_consumable = item_data["is_consumable"] == 1
            defective_count = int(item_data.get("defective_count") or 0)
            today = date.today()

            if is_consumable:
                # Handle consumable items
                return self._calculate_consumable_status(
                    item_id, item_data, today, defective_count
                )
            else:
                # Handle non-consumable items
                return self._calculate_non_consumable_status(
                    item_id, item_data, today, defective_count
                )

        except Exception as e:
            logger.error(
                f"Failed to calculate status for item {item_data.get('id', 'unknown')}: {e}"
            )
            return None

    def _calculate_consumable_status(
        self, item_id: int, item_data: Dict, today: date, defective_count: int
    ) -> ItemStatus:
        """
        Calculate status for consumable items.

        Expiry warning threshold per beta test requirements:
        - Chemicals: 6 months (180 days) before expiration

        Args:
            item_id: Item ID
            item_data: Item data dictionary
            today: Current date

        Returns:
            ItemStatus object
        """
        expiration_date = item_data.get("expiration_date")

        if not expiration_date:
            # No expiration date - assume OK
            return ItemStatus(
                item_id=item_id,
                status="OK",
                has_defective=defective_count > 0,
                defective_count=defective_count,
            )

        try:
            exp_date = date.fromisoformat(expiration_date)
            days_until = (exp_date - today).days

            if days_until < 0:
                # Already expired
                return ItemStatus(
                    item_id=item_id,
                    status="EXPIRED",
                    days_until=days_until,
                    reference_date=exp_date,
                    has_defective=defective_count > 0,
                    defective_count=defective_count,
                )
            elif days_until <= CHEMICAL_EXPIRY_WARNING_DAYS:  # 6 months for chemicals
                # Expiring soon
                return ItemStatus(
                    item_id=item_id,
                    status="EXPIRING",
                    days_until=days_until,
                    reference_date=exp_date,
                    has_defective=defective_count > 0,
                    defective_count=defective_count,
                )
            else:
                # OK
                return ItemStatus(
                    item_id=item_id,
                    status="OK",
                    has_defective=defective_count > 0,
                    defective_count=defective_count,
                )

        except (ValueError, TypeError):
            logger.warning(
                f"Invalid expiration date format for item {item_id}: {expiration_date}"
            )
            return ItemStatus(
                item_id=item_id,
                status="OK",
                has_defective=defective_count > 0,
                defective_count=defective_count,
            )

    def _calculate_non_consumable_status(
        self, item_id: int, item_data: Dict, today: date, defective_count: int
    ) -> ItemStatus:
        """
        Calculate status for non-consumable items.
        Non-consumables can have two statuses: calibration and disposal (expiration).

        Disposal thresholds and calibration applicability are sourced from
        category_config.

        Args:
            item_id: Item ID
            item_data: Item data dictionary
            today: Current date

        Returns:
            ItemStatus object with combined status if multiple alerts exist
        """
        calibration_date = item_data.get("calibration_date")
        expiration_date = item_data.get("expiration_date")  # This is the disposal date
        acquisition_date = item_data.get("acquisition_date")
        category_name = item_data.get("category_name", "")
        category_config = get_category_config(category_name) if category_name else None
        if category_config is None:
            # Fallback keeps unknown/non-standard categories on a conservative,
            # non-calibrated lifecycle policy.
            category_config = get_category_config("Others")

        statuses = []
        reference_dates = []
        days_list = []

        # Calibration status is only applicable for categories that require it.
        if category_config and category_config.has_calibration and calibration_date:
            try:
                cal_date = date.fromisoformat(calibration_date)
                # Next calibration is 1 year after last calibration
                next_cal_date = cal_date + timedelta(days=CALIBRATION_INTERVAL_DAYS)
                days_until_cal = (next_cal_date - today).days

                if days_until_cal < 0:
                    statuses.append("CAL_DUE")
                    reference_dates.append(next_cal_date)
                    days_list.append(days_until_cal)
                elif days_until_cal <= CALIBRATION_WARNING_DAYS:  # 3 months warning
                    statuses.append("CAL_WARNING")
                    reference_dates.append(next_cal_date)
                    days_list.append(days_until_cal)

            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid calibration date format for item {item_id}: {calibration_date}"
                )

        # Check disposal status (stored in expiration_date)
        disposal_date = None
        if expiration_date:
            try:
                disposal_date = date.fromisoformat(expiration_date)
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid disposal date format for item {item_id}: {expiration_date}"
                )
        elif acquisition_date and category_config:
            # No disposal date set - derive from category lifecycle policy.
            try:
                acq_date = date.fromisoformat(acquisition_date)
                disposal_date = category_config.calculate_expiration_date(acq_date)
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid acquisition date format for item {item_id}: {acquisition_date}"
                )

        if disposal_date:
            days_until_disp = (disposal_date - today).days

            if days_until_disp < 0:
                statuses.append("EXPIRED")  # Disposal overdue
                reference_dates.append(disposal_date)
                days_list.append(days_until_disp)
            elif days_until_disp <= NON_CONSUMABLE_WARNING_DAYS:
                statuses.append("EXPIRING")  # Disposal approaching
                reference_dates.append(disposal_date)
                days_list.append(days_until_disp)

        # Return combined status if multiple alerts, otherwise single status or OK
        if not statuses:
            return ItemStatus(
                item_id=item_id,
                status="OK",
                has_defective=defective_count > 0,
                defective_count=defective_count,
            )
        elif len(statuses) == 1:
            return ItemStatus(
                item_id=item_id,
                status=statuses[0],
                days_until=days_list[0],
                reference_date=reference_dates[0],
                has_defective=defective_count > 0,
                defective_count=defective_count,
            )
        else:
            # Multiple statuses - combine with "and" separator
            combined_status = " and ".join(statuses)
            # Use the most urgent (smallest days_until, most negative)
            most_urgent_idx = days_list.index(min(days_list))
            return ItemStatus(
                item_id=item_id,
                status=combined_status,
                days_until=days_list[most_urgent_idx],
                reference_date=reference_dates[most_urgent_idx],
                has_defective=defective_count > 0,
                defective_count=defective_count,
            )


# Global instance
item_status_service = ItemStatusService()
