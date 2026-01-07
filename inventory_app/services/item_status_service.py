"""
Item status service for calculating item status based on expiration and calibration dates.
Handles status calculation for consumables and non-consumables with proper alert logic.

Alert thresholds per beta test requirements:
- Chemicals: 6 months before expiration
- Glassware: 3 years of usage
- Equipment/Apparatuses: 5 years of usage
- Calibration: 3 months before due date (yearly calibration)
"""

from typing import Dict, List, Optional
from datetime import date, timedelta
from dataclasses import dataclass

from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


# Alert threshold constants (in days) per beta test requirements
CHEMICAL_EXPIRY_WARNING_DAYS = 180  # 6 months before expiration
GLASSWARE_DISPOSAL_YEARS = 3  # 3 years of usage
EQUIPMENT_DISPOSAL_YEARS = 5  # 5 years of usage
CALIBRATION_WARNING_DAYS = 90  # 3 months before calibration due
CALIBRATION_INTERVAL_DAYS = 365  # Yearly calibration


@dataclass
class ItemStatus:
    """Represents the status of an inventory item."""

    item_id: int
    status: str  # 'OK', 'EXPIRING', 'EXPIRED', 'CAL_WARNING', 'CAL_DUE'
    days_until: Optional[int] = None
    reference_date: Optional[date] = None


class ItemStatusService:
    """
    Service for calculating item status based on expiration and calibration logic.
    Handles both consumables and non-consumables with appropriate alert periods.
    """

    def __init__(self):
        """Initialize the item status service."""
        logger.info("Item status service initialized")

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
                   i.acquisition_date, c.name as category_name
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
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
            # Get all items with their data, excluding items with 0 stock
            # Items with 0 stock are assumed to be depleted/disposed and should not trigger alerts
            from inventory_app.services.movement_types import MovementType

            query = """
            SELECT i.id, i.name, i.is_consumable, i.expiration_date, i.calibration_date,
                   i.acquisition_date, c.name as category_name
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN (
                SELECT
                    ib.item_id,
                    SUM(ib.quantity_received) -
                    COALESCE(movements.consumed_qty, 0) -
                    COALESCE(movements.disposed_qty, 0) +
                    COALESCE(movements.returned_qty, 0) as total_stock
                FROM Item_Batches ib
                LEFT JOIN (
                    SELECT
                        sm.item_id,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as consumed_qty,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as disposed_qty,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as returned_qty
                    FROM Stock_Movements sm
                    GROUP BY sm.item_id
                ) movements ON ib.item_id = movements.item_id
                GROUP BY ib.item_id
            ) stock ON i.id = stock.item_id
            WHERE COALESCE(stock.total_stock, 0) > 0
            ORDER BY i.name
            """
            params = (
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
            )
            rows = db.execute_query(query, params)
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
            today = date.today()

            if is_consumable:
                # Handle consumable items
                return self._calculate_consumable_status(item_id, item_data, today)
            else:
                # Handle non-consumable items
                return self._calculate_non_consumable_status(item_id, item_data, today)

        except Exception as e:
            logger.error(
                f"Failed to calculate status for item {item_data.get('id', 'unknown')}: {e}"
            )
            return None

    def _calculate_consumable_status(
        self, item_id: int, item_data: Dict, today: date
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
            return ItemStatus(item_id=item_id, status="OK")

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
                )
            elif days_until <= CHEMICAL_EXPIRY_WARNING_DAYS:  # 6 months for chemicals
                # Expiring soon
                return ItemStatus(
                    item_id=item_id,
                    status="EXPIRING",
                    days_until=days_until,
                    reference_date=exp_date,
                )
            else:
                # OK
                return ItemStatus(item_id=item_id, status="OK")

        except (ValueError, TypeError):
            logger.warning(
                f"Invalid expiration date format for item {item_id}: {expiration_date}"
            )
            return ItemStatus(item_id=item_id, status="OK")

    def _calculate_non_consumable_status(
        self, item_id: int, item_data: Dict, today: date
    ) -> ItemStatus:
        """
        Calculate status for non-consumable items.
        Non-consumables can have two statuses: calibration and disposal (expiration).

        Disposal thresholds per beta test requirements:
        - Glassware/Apparatus: 3 years from acquisition
        - Equipment: 5 years from acquisition

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
        category_name = item_data.get("category_name", "").lower()

        statuses = []
        reference_dates = []
        days_list = []

        # Check calibration status
        if calibration_date:
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

        # Determine disposal threshold based on category (beta test requirement #10)
        disposal_years = EQUIPMENT_DISPOSAL_YEARS  # Default: 5 years
        if "apparatus" in category_name or "glass" in category_name:
            disposal_years = GLASSWARE_DISPOSAL_YEARS  # 3 years for glassware/apparatus

        # Check disposal status (stored in expiration_date)
        disposal_date = None
        if expiration_date:
            try:
                disposal_date = date.fromisoformat(expiration_date)
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid disposal date format for item {item_id}: {expiration_date}"
                )
        elif acquisition_date:
            # No disposal date set - use category-based default from acquisition
            try:
                acq_date = date.fromisoformat(acquisition_date)
                disposal_date = acq_date + timedelta(days=disposal_years * 365)
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
            elif days_until_disp <= 90:  # 3 months warning
                statuses.append("EXPIRING")  # Disposal approaching
                reference_dates.append(disposal_date)
                days_list.append(days_until_disp)

        # Return combined status if multiple alerts, otherwise single status or OK
        if not statuses:
            return ItemStatus(item_id=item_id, status="OK")
        elif len(statuses) == 1:
            return ItemStatus(
                item_id=item_id,
                status=statuses[0],
                days_until=days_list[0],
                reference_date=reference_dates[0],
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
            )


# Global instance
item_status_service = ItemStatusService()
