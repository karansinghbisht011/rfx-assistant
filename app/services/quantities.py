"""Parse quantity text such as '4', '1,000', 'ten', 'a dozen' or '10-12'."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app import config

_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}
_RANGE = re.compile(r"^\s*[\d.,]+\s*(?:-|–|to)\s*[\d.,]+\s*$", re.I)


@dataclass(frozen=True)
class QuantityParse:
    value: Decimal | None
    problem: str | None = None  # None, "range", "unparsable", "nonpositive" or "too_large"


def parse_quantity(text: str | None) -> QuantityParse:
    if text is None or not text.strip():
        return QuantityParse(None)
    t = text.strip().lower()
    if _RANGE.match(t):
        return QuantityParse(None, "range")
    value: Decimal | None = None
    dozen = re.fullmatch(r"(?:(a|one|two|three|four|five|six)\s+)?dozen", t)
    if dozen:
        multiplier = 1 if dozen.group(1) in (None, "a", "one") else _WORDS[dozen.group(1)]
        value = Decimal(12 * multiplier)
    elif t in _WORDS:
        value = Decimal(_WORDS[t])
    else:
        cleaned = re.sub(r"(?<=\d),(?=\d)", "", t)
        if re.fullmatch(r"\d+(\.\d+)?", cleaned):
            try:
                value = Decimal(cleaned)
            except InvalidOperation:
                value = None
    if value is None:
        return QuantityParse(None, "unparsable")
    return check_quantity(value)


def check_quantity(value: Decimal) -> QuantityParse:
    if value <= 0:
        return QuantityParse(None, "nonpositive")
    if value > config.QUANTITY_CAP:
        return QuantityParse(None, "too_large")
    return QuantityParse(value)


def format_quantity(value: Decimal | None) -> str:
    """Plain display without trailing zeros: 4, 2.5, 1000."""
    if value is None:
        return ""
    text = format(value.normalize(), "f")
    return text
