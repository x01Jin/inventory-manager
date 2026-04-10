"""Reference and size normalization helpers.

Single-purpose helpers used across models, services, and UI to keep duplicate
matching and size formatting behavior consistent.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Optional


_WHITESPACE_PATTERN = re.compile(r"\s+")
_NUMBER_UNIT_PATTERN = re.compile(r"^([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)$")

_UNIT_CANONICAL_MAP = {
    "ml": "mL",
    "milliliter": "mL",
    "milliliters": "mL",
    "millilitre": "mL",
    "millilitres": "mL",
    "l": "L",
    "lt": "L",
    "lts": "L",
    "ltr": "L",
    "liter": "L",
    "liters": "L",
    "litre": "L",
    "litres": "L",
    "g": "g",
    "gm": "g",
    "gms": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "mg": "mg",
    "milligram": "mg",
    "milligrams": "mg",
    "gal": "gal",
    "galon": "gal",
    "galons": "gal",
    "gallon": "gal",
    "gallons": "gal",
}


def normalize_whitespace(value: Optional[str]) -> str:
    """Return string with trimmed and collapsed internal whitespace."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return _WHITESPACE_PATTERN.sub(" ", text)


def build_reference_compare_key(value: Optional[str]) -> str:
    """Build compare key for case-insensitive duplicate detection."""
    return normalize_whitespace(value).lower()


def _normalize_number_token(token: str) -> str:
    """Normalize numeric token to a compact decimal representation."""
    try:
        parsed = Decimal(token)
    except (InvalidOperation, ValueError):
        return token

    if parsed == parsed.to_integral():
        return str(parsed.quantize(Decimal("1")))

    text = format(parsed.normalize(), "f")
    text = text.rstrip("0").rstrip(".")
    return text or "0"


def normalize_metric_size_value(value: Optional[str]) -> Optional[str]:
    """Normalize size value into canonical metric casing when possible.

    Examples:
    - 10ml -> 10 mL
    - 2.5 l -> 2.5 L
    - 125 GMS -> 125 g

    For non-matching free-form values, whitespace is normalized but text is
    otherwise preserved.
    """
    text = normalize_whitespace(value)
    if not text:
        return None

    match = _NUMBER_UNIT_PATTERN.fullmatch(text)
    if not match:
        return text

    raw_number, raw_unit = match.groups()
    canonical_unit = _UNIT_CANONICAL_MAP.get(raw_unit.lower())
    if canonical_unit is None:
        return text

    normalized_number = _normalize_number_token(raw_number)
    return f"{normalized_number} {canonical_unit}"


def build_size_compare_key(value: Optional[str]) -> str:
    """Build compare key for size values, tolerant to unit/case/spacing variants."""
    normalized = normalize_metric_size_value(value)
    if not normalized:
        return ""
    return normalized.replace(" ", "").lower()
