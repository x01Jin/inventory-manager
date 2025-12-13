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


def allowed_values() -> List[str]:
    """Return a list of allowed movement type values."""
    return [m.value for m in MovementType]
