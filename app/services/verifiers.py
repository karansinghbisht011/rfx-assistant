"""RFQ verifiers (R-series, section 13). Pure functions; each returns Review flags or a verdict."""

import re
from decimal import Decimal

from app import config
from app.schemas.flags import ReviewEntry, ReviewFlag
from app.schemas.rfq import RFQ, RequestedItem
from app.services import units
from app.services.catalogue_service import normalize
from app.services.quantities import format_quantity

# Flags the buyer can accept as-is. The rest must be fixed by editing the line.
ACCEPTABLE_CODES = {"R4", "R7", "R12", "R13", "R14", "R17"}

_INJECTION = re.compile(r"ignore (all |any )?(previous|prior|above)|system prompt|disregard", re.I)


def _flag(item: RequestedItem, code: str, message: str, severity: str = "review") -> ReviewFlag:
    return ReviewFlag(
        code=code,
        severity=severity,
        scope="rfq_item",
        scope_id=item.item_id,
        message=message,
        resolution="accepted" if code in item.acknowledged else None,
    )


def check_input(text: str) -> str | None:
    """R1: reason the request cannot be processed, or None. Runs before any model call."""
    stripped = text.strip()
    if not stripped:
        return "Tell me what you need: list the products, with quantities and units if you have them."
    if len(stripped) > config.MAX_INPUT_CHARS:
        return f"Your request is too long ({len(stripped)} characters). Keep it under {config.MAX_INPUT_CHARS}."
    letters = sum(c.isalpha() for c in stripped)
    if letters < 0.4 * len(stripped):
        return "That doesn't look like a list of products."
    return None


def has_injection_text(text: str) -> bool:
    """R18: informational only; the input is always treated as data."""
    return bool(_INJECTION.search(text))


def _contains_phrase(text: str, phrase: str) -> bool:
    """Whole-word containment on normalized text, so '4' does not match inside '14'."""
    return bool(phrase) and f" {normalize(phrase)} " in f" {normalize(text)} "


def wording_in_input(original_text: str, request_text: str) -> bool:
    """R4: the item's wording really appears in what the buyer typed."""
    return _contains_phrase(request_text, original_text)


def quantity_in_input(quantity_text: str | None, request_text: str) -> bool:
    """R5: the quantity text appears in the request (digits or words)."""
    return bool(quantity_text) and _contains_phrase(request_text, quantity_text)


def rfq_level_flags(parsed_count: int, request_text: str) -> list[ReviewFlag]:
    """R14: many separated segments but few parsed items suggests items were merged."""
    lines = [s for s in request_text.splitlines() if s.strip()]
    if len(lines) >= 3:  # one item per line is the norm; a compound line can only add items
        lost = parsed_count < len(lines)
    else:
        segments = [s for s in re.split(r"[\n;,]| and ", request_text) if s.strip()]
        lost = len(segments) >= 3 and parsed_count < len(segments) - 1
    if lost:
        return [
            ReviewFlag(
                code="R14",
                severity="review",
                scope="rfq",
                scope_id="rfq",
                message="Some items in your request may have been combined. Check that every item appears below.",
            )
        ]
    return []


def compute_item_flags(item: RequestedItem, duplicate_codes: set[str]) -> list[ReviewFlag]:
    """Derive the item's flags from its current state (R4, R6, R7, R8, R12, R13, R17)."""
    flags: list[ReviewFlag] = []
    label = item.original_text

    if "wording_unverified" in item.parse_issues:
        flags.append(_flag(item, "R4", f"We could not confirm “{label}” in your request. Check this line."))

    if item.quantity is None:
        if "quantity_range" in item.parse_issues:
            msg = f"The quantity for “{label}” looks like a range. Enter a single number."
        elif "quantity_unverified" in item.parse_issues:
            msg = f"No quantity was stated for “{label}”. Enter one."
        else:
            msg = f"Enter a quantity for “{label}”."
        flags.append(_flag(item, "R6", msg, "block"))
    elif item.quantity <= 0 or item.quantity > config.QUANTITY_CAP:
        flags.append(_flag(item, "R6", f"The quantity for “{label}” must be a positive number.", "block"))
    elif units.is_discrete(item.unit) and item.quantity != item.quantity.to_integral_value():
        flags.append(
            _flag(item, "R7", f"{format_quantity(item.quantity)} {item.unit} for “{label}” is not a whole number.")
        )

    if item.unit is None:
        if item.unit_text:
            msg = f"The unit “{item.unit_text}” for “{label}” is not recognised. Choose one."
        else:
            msg = f"Choose a unit for “{label}”."
        flags.append(_flag(item, "R8", msg, "block"))

    if not item.buyer_selected:
        if item.match_status == "ambiguous":
            flags.append(_flag(item, "R12", f"Several catalogue items could match “{label}”. Choose the right one."))
        elif item.match_status == "unmatched":
            flags.append(
                _flag(item, "R17", f"“{label}” was not found in the catalogue. Pick an item, or keep your wording.")
            )

    if item.catalogue_code and item.catalogue_code in duplicate_codes:
        flags.append(_flag(item, "R13", f"“{label}” matches the same catalogue item as another line."))
    return flags


def refresh_flags(rfq: RFQ) -> None:
    """Recompute every item's flags from its state, keeping the buyer's acknowledgements."""
    counts: dict[str, int] = {}
    for item in rfq.items:
        if item.catalogue_code:
            counts[item.catalogue_code] = counts.get(item.catalogue_code, 0) + 1
    duplicates = {code for code, n in counts.items() if n > 1}
    for item in rfq.items:
        item.flags = compute_item_flags(item, duplicates)
    sync_log(rfq)


def sync_entries(log: list[ReviewEntry], flags: list[ReviewFlag], live: set[str], blocking: set[str]) -> list[ReviewEntry]:
    """Keep a Review summary in step with the flags: an entry is open until the buyer accepts it
    (reviewed) or the problem goes away (fixed). Entries never disappear; those whose subject is gone do."""
    current = {f"{f.scope_id}:{f.code}": f for f in flags if f.severity in ("block", "review")}
    known = {e.key: e for e in log}
    for key, flag in current.items():
        entry = known.get(key)
        if entry is None:
            entry = ReviewEntry(key=key, code=flag.code, scope_id=flag.scope_id, message=flag.message,
                                blocking=flag.code in blocking)
            log.append(entry)
        entry.status = "reviewed" if flag.resolution == "accepted" else "open"
        if entry.status == "open":
            entry.message = flag.message
    for entry in log:
        if entry.key not in current and entry.status != "reviewed":
            entry.status = "fixed"
    return [e for e in log if e.scope_id in live]


def sync_log(rfq: RFQ) -> None:
    live = {i.item_id for i in rfq.items} | {"rfq"}
    rfq.review_log = sync_entries(rfq.review_log, all_flags(rfq), live, {"R6", "R8"})


def all_flags(rfq: RFQ) -> list[ReviewFlag]:
    return list(rfq.flags) + [f for item in rfq.items for f in item.flags]


def open_flags(rfq: RFQ) -> list[ReviewFlag]:
    return [f for f in all_flags(rfq) if f.open and f.severity in ("block", "review")]


def needs_review(item: RequestedItem) -> bool:
    """True while the line has an unresolved Review or Fix flag."""
    return any(f.open and f.severity in ("block", "review") for f in item.flags)


def is_blocking(item: RequestedItem) -> bool:
    """True while the line has a flag that must be fixed by editing (quantity or unit)."""
    return any(f.open and f.code in ("R6", "R8") for f in item.flags)


SHORT_LABELS = {
    "R4": "Check wording", "R7": "Not a whole number", "R12": "Choose an item",
    "R13": "Duplicate item", "R17": "Not in catalogue",
}


def short_label(flag: ReviewFlag) -> str:
    """A few words for the table's status column."""
    if flag.code == "R6":
        return "Quantity is a range" if "range" in flag.message else "Quantity needed"
    if flag.code == "R8":
        return "Unit needed" if "not recognised" not in flag.message else "Unit not recognised"
    return SHORT_LABELS.get(flag.code, "Review")


def can_save(rfq: RFQ) -> bool:
    """Every flag must be fixed or acknowledged, and there must be at least one line."""
    return bool(rfq.items) and not open_flags(rfq)


def quantity_to_decimal(value: float | int | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
