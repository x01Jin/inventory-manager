"""
Centralized movement type enumeration and SQL helpers.
Provides a single source of truth for Stock_Movements.movement_type values
and helpers for safely building SQL pieces where necessary.
"""

from enum import Enum
from typing import List


class MovementType(Enum):
    CONSUMPTION = "CONSUMPTION"
    RESERVATION = "RESERVATION"
    RETURN = "RETURN"
    DISPOSAL = "DISPOSAL"
    REQUEST = "REQUEST"
    LOST = "LOST"


def allowed_values() -> List[str]:
    """Return a list of allowed movement type values."""
    return [m.value for m in MovementType]


def sql_values_in_clause() -> str:
    """Return an SQL IN-list like ('CONSUMPTION','RESERVATION',...)
    for use in static SQL building. Values are constant and safe.
    """
    vals = allowed_values()
    return "(" + ",".join(f"'{v}'" for v in vals) + ")"
