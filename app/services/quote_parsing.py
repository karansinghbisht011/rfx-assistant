"""Turn the verbatim text Gemini returns (prices, quantities, dates, tax wording) into values.

Pure functions. Anything that cannot be read stays None: a missing price is never turned into zero.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app.services.quantities import parse_quantity

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

AMBIGUOUS_DOLLAR = "$?"


def _decimal(token: str) -> Decimal | None:
    try:
        return Decimal(token.replace(",", ""))
    except InvalidOperation:
        return None


def numbers_in(text: str) -> set[Decimal]:
    """Every number in a piece of text, with thousands separators (Western or Indian) removed."""
    return {d for t in _NUMBER.findall(text or "") if (d := _decimal(t)) is not None}


def number_in_source(value: Decimal | None, source: str) -> bool:
    """True when the parsed value really appears in the source row (R/Q10 grounding)."""
    return value is not None and value in numbers_in(source)


def detect_currency(*texts: str | None) -> str | None:
    """ISO code from symbols and words. A bare '$' is ambiguous (USD, CAD, AUD...) and is reported as such."""
    blob = " ".join(t for t in texts if t).lower()
    if not blob:
        return None
    if re.search(r"₹|\brs\b\.?|\binr\b|\brupees?\b", blob):
        return "INR"
    if re.search(r"\busd\b|us\$|\bus dollars?\b", blob):
        return "USD"
    if re.search(r"\beur\b|€|\beuros?\b", blob):
        return "EUR"
    if re.search(r"\bgbp\b|£", blob):
        return "GBP"
    if "$" in blob:
        return AMBIGUOUS_DOLLAR
    return None


def parse_amount(text: str | None) -> Decimal | None:
    """First amount in the text: 'Rs 47,000 each' -> 47000; '1.25 lakh' -> 125000; 'on request' -> None."""
    if not text:
        return None
    match = _NUMBER.search(text)
    if not match:
        return None
    value = _decimal(match.group())
    if value is None:
        return None
    tail = text[match.end():].lower()
    if re.match(r"\s*(lakh|lac|lakhs)\b", tail):
        value *= 100_000
    elif re.match(r"\s*crores?\b", tail):
        value *= 10_000_000
    return value


def parse_quote_quantity(text: str | None) -> Decimal | None:
    """'150 mtr' -> 150; 'a dozen' -> 12; ranges and nonsense -> None."""
    if not text:
        return None
    result = parse_quantity(text)
    if result.value is not None:
        return result.value
    amount = parse_amount(text)
    return amount if amount is not None and amount > 0 and "-" not in text else None


@dataclass(frozen=True)
class Basis:
    quantity: Decimal | None   # 100 for "per 100"; 1 for "each"/"per kg"; None when absent
    recognised: bool = True    # False when basis text is present but could not be read


def parse_basis(*texts: str | None) -> Basis:
    blob = " ".join(t for t in texts if t).lower()
    if not blob.strip():
        return Basis(None)
    match = re.search(r"(?:per|/)\s*(\d+(?:\.\d+)?)\s*(?:nos?|pcs?|pieces?|units?|kg|m|mtrs?|ltrs?|litres?|sets?|pairs?)?\b", blob)
    if match:
        n = _decimal(match.group(1))
        if n and n > 0:
            return Basis(n)
    if re.search(r"\beach\b|\bper\s+(?:unit|piece|pc|no|nos|kg|kgs|m|mtr|metre|meter|litre|ltr|set|pair|drum|pack|box|roll)\b|/\s*(?:unit|kg|m|mtr|ltr|set|pair)\b", blob):
        return Basis(Decimal(1))
    return Basis(None, recognised=False)


def detect_tax_basis(*texts: str | None) -> str:
    """'inclusive', 'exclusive' or 'unclear' from the wording around GST/tax."""
    blob = " ".join(t for t in texts if t).lower()
    if "gst" not in blob and "tax" not in blob:
        return "unclear"
    inclusive = bool(re.search(r"inclusive|incl\.?\b|including|incl of", blob))
    exclusive = bool(re.search(r"exclusive|excl\.?\b|excluding|extra|\+\s*gst|plus gst|will be added|to be added|additional", blob))
    if inclusive and not exclusive:
        return "inclusive"
    if exclusive and not inclusive:
        return "exclusive"
    return "unclear"


def parse_date_text(text: str | None) -> date | None:
    """Reads '03 Oct 2026', '3 October 2026', '03/10/2026', '2026-10-03' and dates inside longer text."""
    if not text:
        return None
    m = re.search(r"(\d{1,2})[\s\-/.,]*([A-Za-z]{3,9})[\s\-/.,]*(\d{4})", text)
    if m and m.group(2)[:3].lower() in _MONTHS:
        try:
            return date(int(m.group(3)), _MONTHS[m.group(2)[:3].lower()], int(m.group(1)))
        except ValueError:
            return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def parse_validity(text: str | None, quote_date: date | None) -> date | None:
    """Expiry date from '15 days from date of quotation' (needs the quote date) or an explicit date."""
    if not text:
        return None
    explicit = parse_date_text(text)
    if explicit:
        return explicit
    m = re.search(r"(\d+)\s*days", text.lower())
    if m and quote_date:
        return quote_date + timedelta(days=int(m.group(1)))
    return None
