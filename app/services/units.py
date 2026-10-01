"""Canonical units, aliases and exact conversions (section 7 of the implementation plan).

Conversions exist only within mass, length and volume. Count units are never converted
into each other, because a Box or Pack has no fixed size.
"""

import re
from decimal import Decimal

from app import config

_ALIASES = {
    "Nos": ["nos", "no", "nr", "pcs", "pc", "piece", "pieces", "each", "ea", "unit", "units", "number", "numbers"],
    "Set": ["set", "sets"],
    "Pair": ["pair", "pairs"],
    "Kit": ["kit", "kits"],
    "Kg": ["kg", "kgs", "kilo", "kilos", "kilogram", "kilograms"],
    "Tonne": ["tonne", "tonnes", "ton", "tons", "mt", "metric ton", "metric tons"],
    "Metre": ["m", "mtr", "mtrs", "meter", "meters", "metre", "metres"],
    "Litre": ["l", "ltr", "ltrs", "liter", "liters", "litre", "litres"],
    "Box": ["box", "boxes"],
    "Pack": ["pack", "packs", "packet", "packets"],
    "Roll": ["roll", "rolls"],
    "Drum": ["drum", "drums"],
}
# Units that vendors may quote in; converted to the RFQ unit, never offered on RFQ lines.
_QUOTE_ONLY_ALIASES = {
    "g": ["g", "gm", "gms", "gram", "grams"],
    "cm": ["cm", "centimetre", "centimetres", "centimeter", "centimeters"],
    "mm": ["mm", "millimetre", "millimetres", "millimeter", "millimeters"],
    "km": ["km", "kilometre", "kilometres", "kilometer", "kilometers"],
    "ml": ["ml", "millilitre", "millilitres", "milliliter", "milliliters"],
    "kl": ["kl", "kilolitre", "kilolitres", "kiloliter", "kiloliters"],
}

_LOOKUP = {alias: unit for unit, aliases in _ALIASES.items() for alias in aliases}
_QUOTE_LOOKUP = {alias: unit for unit, aliases in _QUOTE_ONLY_ALIASES.items() for alias in aliases}

# unit -> (dimension, factor to the dimension's base unit); bases are Kg, Metre, Litre
_FACTORS: dict[str, tuple[str, Decimal]] = {
    "Kg": ("mass", Decimal("1")),
    "Tonne": ("mass", Decimal("1000")),
    "g": ("mass", Decimal("0.001")),
    "Metre": ("length", Decimal("1")),
    "cm": ("length", Decimal("0.01")),
    "mm": ("length", Decimal("0.001")),
    "km": ("length", Decimal("1000")),
    "Litre": ("volume", Decimal("1")),
    "ml": ("volume", Decimal("0.001")),
    "kl": ("volume", Decimal("1000")),
}


def normalize_unit(text: str | None, *, quote_side: bool = False) -> str | None:
    """Map free text to a canonical unit, or None if unrecognised. Never guesses."""
    if not text:
        return None
    key = re.sub(r"[.\s]+", " ", text.strip().lower()).strip()
    if key in _LOOKUP:
        return _LOOKUP[key]
    if quote_side:
        return _QUOTE_LOOKUP.get(key)
    return None


def dimension(unit: str) -> str:
    if unit in config.COUNT_UNITS:
        return "count"
    return _FACTORS[unit][0]


def is_discrete(unit: str | None) -> bool:
    """Units whose quantities should be whole numbers."""
    return unit in config.COUNT_UNITS


def convert(quantity: Decimal, from_unit: str, to_unit: str) -> Decimal | None:
    """Convert within one physical dimension; None when units are not comparable."""
    if from_unit == to_unit:
        return quantity
    if from_unit not in _FACTORS or to_unit not in _FACTORS:
        return None
    from_dim, from_factor = _FACTORS[from_unit]
    to_dim, to_factor = _FACTORS[to_unit]
    if from_dim != to_dim:
        return None
    return quantity * from_factor / to_factor
