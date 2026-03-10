"""
Stock parsing utilities.

Single-purpose functions for parsing free-form 'stocks' cells from imported Excel rows.

Behavior summary:
- Numeric-only values -> treated as integer quantity (floats coerced to int).
- Values with size units (ml, l, g, kg, mg, gal, etc), either attached to the number (e.g., "900ml") or separated by space ("1 L") -> treated as a usable quantity and size=<matched substring>. Some units are scaled to base usable units (`L` family -> ml, `kg` family -> g, `gal/galon` family -> project-standard 1000 scaling) so partial requisitions work with integer values.
- Packaging counts with piece details ("1 box (100pcs)", "2 packs of 50 pcs") -> quantity is converted to usable pieces (leading count * per-package piece count), with details retained in notes.
- Other leading counts with words ("2 sets", "10 boxes") -> leading integer is used as quantity; parenthetical or trailing detail is returned as notes.
- Empty / None -> quantity 0.
- If no numeric information is present, a ValueError is raised (same behavior as previous importer: invalid stock value skips the row).

All parsing is case-insensitive for unit matching; returned size preserves the original substring (trimmed) to keep spacing behavior predictable.
"""

from __future__ import annotations

import re
from typing import Dict, Any

# Units considered to be size indicators (volume/mass). Case-insensitive.
_SIZE_UNITS = {
    "ml",
    "milliliter",
    "milliliters",
    "millilitre",
    "millilitres",
    "l",
    "lt",
    "lts",
    "g",
    "gm",
    "gms",
    "gram",
    "grams",
    "kg",
    "kilo",
    "kilos",
    "kilogram",
    "kilograms",
    "mg",
    "milligram",
    "milligrams",
    "gal",
    "galon",
    "galons",
    "gallon",
    "gallons",
    "liter",
    "liters",
    "litre",
    "litres",
    "ltr",
}

# A broader set that includes "pcs" / "pieces" for notes detection
_PIECE_UNITS = {"pcs", "pieces", "pc"}

# Container words that indicate package-based counts.
_PACKAGING_UNITS = {
    "box",
    "boxes",
    "pack",
    "packs",
    "package",
    "packages",
    "pkg",
    "pkgs",
    "case",
    "cases",
    "carton",
    "cartons",
    "bundle",
    "bundles",
}

# Regex to find a number optionally with attached unit (e.g. '900ml' or '1.1 ml')
_RE_NUMBER_WITH_UNIT = re.compile(r"(?i)(\d+(?:\.\d+)?)(?:\s*)?([a-z]+)\b")

# Regex to find a leading integer
_RE_LEADING_INT = re.compile(r"^\s*(\d+)\b")

# Regex to capture parenthetical trailing info like '(100pcs)'
_RE_PAREN_INFO = re.compile(r"\(([^)]+)\)")

# Regex to capture leading count + container unit, e.g. '2 boxes ...'
_RE_LEADING_COUNT_WITH_UNIT = re.compile(r"^\s*(\d+)\s*([a-z]+)\b", re.I)

# Regex to capture a piece count mention, e.g. '100pcs' or '50 pieces'
_RE_PIECE_COUNT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:pcs|pieces|pc)\b", re.I)

# Multipliers applied to the numeric part for units that represent larger
# containers. This keeps requisitions integer-based while allowing partial use.
# Example: 2.5 L -> 2500 usable units (ml), 1 kilo -> 1000 usable units (g),
# 1.1 gal -> 1100 usable units (project-standard conversion behavior).
_UNIT_MULTIPLIERS = {
    "l": 1000,
    "liter": 1000,
    "liters": 1000,
    "litre": 1000,
    "litres": 1000,
    "ltr": 1000,
    "lt": 1000,
    "lts": 1000,
    "kg": 1000,
    "kilo": 1000,
    "kilos": 1000,
    "kilogram": 1000,
    "kilograms": 1000,
    "gal": 1000,
    "galon": 1000,
    "galons": 1000,
    "gallon": 1000,
    "gallons": 1000,
}


def parse_stock_value(raw: Any) -> Dict[str, Any]:
    """Parse a raw 'stocks' cell and return structured info.

    Returns a dict with keys:
      - quantity: int
      - size: Optional[str] (e.g., '900ml' or '1 L') if a size unit was found
      - notes: Optional[str] for additional details (e.g., '(100pcs)', 'set of 8 pieces')

    Raises ValueError if the raw value contains no parseable numeric information and is
    not empty/None.
    """
    if raw is None:
        return {"quantity": 0, "size": None, "notes": None}

    # If already numeric (int/float), coerce to int
    if isinstance(raw, (int,)):
        return {"quantity": int(raw), "size": None, "notes": None}
    if isinstance(raw, float):
        return {"quantity": int(raw), "size": None, "notes": None}

    s = str(raw).strip()
    if s == "":
        return {"quantity": 0, "size": None, "notes": None}

    lowered = s.lower()

    # First try to find a number with a recognized size unit anywhere in the string.
    # For values like '900ml', use the numeric part as stock quantity so
    # consumables can be requested/returned in partial usable amounts.
    # For larger units, convert to base usable units (e.g., '1 L' -> 1000).
    for m in _RE_NUMBER_WITH_UNIT.finditer(s):
        unit = m.group(2)
        if unit.lower() in _SIZE_UNITS:
            # Use the exact substring matched from the original string
            # (preserving spaces/case close to input) for the size field.
            start, end = m.span()
            size_substr = s[start:end]
            qty_raw = m.group(1)
            multiplier = _UNIT_MULTIPLIERS.get(unit.lower(), 1)
            quantity = int(float(qty_raw) * multiplier)
            return {"quantity": quantity, "size": size_substr.strip(), "notes": None}

    # If no size units found, try for a leading integer quantity
    m_lead = _RE_LEADING_INT.search(s)
    if m_lead:
        quantity = int(m_lead.group(1))
        notes = None

        # Convert package counts to usable piece counts when a per-package piece
        # quantity is present (e.g. '1 box (100pcs)' -> 100).
        pack_match = _RE_LEADING_COUNT_WITH_UNIT.search(s)
        if pack_match:
            pack_unit = pack_match.group(2).lower()
            if pack_unit in _PACKAGING_UNITS:
                piece_match = _RE_PIECE_COUNT.search(s)
                if piece_match:
                    try:
                        piece_count = int(float(piece_match.group(1)))
                        if piece_count > 0:
                            quantity = quantity * piece_count
                    except Exception:
                        pass

        # If there's parenthetical info capture it to notes
        par = _RE_PAREN_INFO.search(s)
        if par:
            notes = par.group(0)  # include parentheses
        else:
            # capture 'of N pieces' style descriptions as notes (e.g., '1 set of 8 pieces')
            # look for 'of' followed by digits/pcs/pieces
            of_match = re.search(r"of\s+\d+\s*(?:pcs|pieces|pc)?", lowered)
            if of_match:
                notes = of_match.group(0)
        return {"quantity": quantity, "size": None, "notes": notes}

    # As a last resort, try to parse any float present in the string
    m_any_num = re.search(r"(\d+(?:\.\d+)?)", s)
    if m_any_num:
        # if a number exists but no unit and not leading integer (e.g., 'approx 0.5 bottle'), coerce to int
        try:
            quantity = int(float(m_any_num.group(1)))
            return {"quantity": quantity, "size": None, "notes": None}
        except Exception:
            pass

    raise ValueError(f"Invalid stock value: {raw}")


# For convenience, small helper that behaves like the old _parse_int but uses new parser
def parse_stock_quantity(raw: Any) -> int:
    info = parse_stock_value(raw)
    return int(info.get("quantity", 0))
