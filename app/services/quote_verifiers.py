"""Quotation verifiers (Q-series and M-series, section 13). Pure functions over a Quotation and the RFQ.

Flags are derived from the data every time, so they follow the buyer's Accept and Exclude actions.
Excluded lines and quotations carry no flags. Nothing here edits a number.
"""

import re
import statistics
from datetime import date
from decimal import Decimal

from app import config, state
from app.schemas.flags import ReviewFlag
from app.schemas.quotation import Quotation, QuotedLineItem
from app.schemas.rfq import RFQ, RequestedItem
from app.services import units, verifiers
from app.services.quote_parsing import AMBIGUOUS_DOLLAR, number_in_source, parse_amount

# The buyer can accept these as they are. Everything else is resolved by excluding the line or quotation.
ACCEPTABLE = {"Q4", "Q5", "Q6", "Q9", "Q10", "Q13", "Q16", "Q17", "Q18", "Q19", "Q22", "Q23", "Q24", "Q25",
              "M2", "M3", "M7", "M8", "M9"}
BLOCKING = {"Q11", "Q12", "Q15", "Q20", "Q21", "Q26", "M4"}
_INJECTION = re.compile(r"ignore (all |any )?(previous|prior|above)|system prompt|disregard (the|all)", re.I)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def vendor_key(name: str | None) -> str:
    """Vendor name without legal suffixes, for spotting two files from one vendor (Q26)."""
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", _norm(name or ""))
    cleaned = re.sub(r"\b(pvt|private|ltd|limited|llp|inc|co|corp|company|the)\b", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _flag(scope: str, scope_id: str, code: str, message: str, acknowledged: list[str]) -> ReviewFlag:
    return ReviewFlag(code=code, severity="review", scope=scope, scope_id=scope_id, message=message,
                      resolution="accepted" if code in acknowledged else None)


def active_quotes(quotes: list[Quotation]) -> list[Quotation]:
    return [q for q in quotes if q.status not in ("rejected", "failed") and not q.excluded]


def _adjusted_price(line: QuotedLineItem, quote: Quotation) -> Decimal | None:
    """Price per unit with tax backed out only when the vendor states the tax is included and gives the rate."""
    price = line.price_per_unit
    if price is None:
        return None
    from app.services.quote_parsing import detect_tax_basis

    basis = detect_tax_basis(line.tax_text) if line.tax_text else quote.tax_basis
    if basis == "inclusive" and line.tax_text:
        rate = parse_amount(re.sub(r".*?(\d+(?:\.\d+)?)\s*%.*", r"\1", line.tax_text, flags=re.S))
        if rate and 0 < rate < 50:
            return price / (1 + rate / 100)
    return price


def peer_prices(quotes: list[Quotation]) -> dict[str, list[tuple[str, Decimal]]]:
    """RFQ item id -> (quote id, price per unit) for every usable matched line, in INR and the RFQ's unit."""
    out: dict[str, list[tuple[str, Decimal]]] = {}
    for q in active_quotes(quotes):
        for line in q.lines:
            if line.excluded or not line.matched_rfq_item_id or line.match_status not in ("matched", "possible"):
                continue
            if line.currency != "INR" or not line.unit_price:
                continue
            price = _adjusted_price(line, q)
            if price is not None:
                out.setdefault(line.matched_rfq_item_id, []).append((q.quotation_id, price))
    return out


def line_flags(line: QuotedLineItem, quote: Quotation, rfq: RFQ, peers: dict) -> list[ReviewFlag]:
    flags: list[ReviewFlag] = []
    ack = line.acknowledged
    items = {i.item_id: i for i in rfq.items}
    item: RequestedItem | None = items.get(line.matched_rfq_item_id) if line.matched_rfq_item_id else None
    label = line.source_description or line.row_ref

    def add(code: str, message: str) -> None:
        flags.append(_flag("quote_line", line.line_id, code, message, ack))

    if item is None:  # a product the buyer did not ask for: shown as "not on your RFQ", not flagged
        return flags
    row_text = quote.source_rows.get(line.row_ref)
    if not quote.read_from_image:
        if row_text is None or _norm(line.source_quote) not in _norm(row_text):
            add("Q9", f"We could not find “{label}” in the document where it was read from. Check it.")
        elif any(v is not None and not number_in_source(v, row_text) for v in (line.unit_price, line.quantity)):
            add("Q10", f"A number for “{label}” does not appear in the source row. Check it.")

    if line.unit_price is None:
        what = "could not be read" if line.unit_price_text else "was not given"
        add("Q11", f"The price for “{label}” {what}." + (f" It says: “{line.remarks}”." if line.remarks and not line.unit_price_text else ""))
    elif line.unit_price == 0:
        add("Q12", f"“{label}” is priced at zero. Is it free, or missing?")
    elif line.price_basis_text and line.price_basis_quantity is None:
        add("Q21", f"The price basis “{line.price_basis_text}” for “{label}” could not be read.")

    if line.quantity is not None and line.unit_price is not None and line.line_total is not None and line.currency == quote.currency:
        expected = line.quantity * (line.price_per_unit or Decimal(0))
        if abs(expected - line.line_total) > max(Decimal(1), line.line_total * Decimal(str(config.PRICE_TOLERANCE))):
            add("Q16", f"“{label}”: quantity × price does not match the amount shown.")

    if line.unit_price is None:  # nothing to compare: the missing price is the issue, not the unit
        pass
    elif not line.unit_text:
        add("Q19", f"No unit is stated for “{label}”. Accepting means the RFQ unit ({item.unit}) is assumed.")
    elif line.unit is None:
        add("Q20", f"The unit “{line.unit_text}” for “{label}” is not recognised.")
    elif item.unit and line.unit != item.unit and units.convert(Decimal(1), line.unit, item.unit) is None:
        add("Q20", f"“{label}” is quoted per {line.unit_text}, but your RFQ asks for {item.unit}. They cannot be compared.")

    if line.match_status == "possible":
        diff = f" Differences: {', '.join(line.match_differences)}." if line.match_differences else ""
        add("M3" if line.match_differences else "M2", f"“{label}” may be your “{item.catalogue_title or item.original_text}”.{diff}")
    if line.is_alternate:
        add("M9", f"“{label}” is offered as an alternative or substitute.")
    if (line.quantity is not None and item.quantity is not None and line.quantity != item.quantity
            and line.unit == item.unit):
        add("M7", f"“{label}”: the vendor quotes {line.quantity:g} but your RFQ asks for {item.quantity:g}.")
    if line.moq is not None and item.quantity is not None and line.moq > item.quantity:
        add("M8", f"“{label}” has a minimum order of {line.moq:g}, above your {item.quantity:g}.")

    others = [p for qid, p in peers.get(item.item_id, []) if qid != quote.quotation_id]
    mine = _adjusted_price(line, quote)
    if mine and len(others) >= 2 and line.currency == "INR" and (not item.unit or line.unit in (None, item.unit)):
        median = statistics.median(others)
        factor = Decimal(config.PRICE_OUTLIER_FACTOR)
        if median > 0 and (mine > median * factor or mine < median / factor):
            add("Q22", f"The price for “{label}” is far from the other vendors' prices. Possible unit or decimal slip.")
    return flags


def _mark_options(quote: Quotation, rfq: RFQ) -> list[ReviewFlag]:
    flags = []
    items = {i.item_id: i for i in rfq.items}
    groups: dict[str, list[QuotedLineItem]] = {}
    for line in quote.lines:
        if not line.excluded and line.matched_rfq_item_id and line.match_status in ("matched", "possible"):
            groups.setdefault(line.matched_rfq_item_id, []).append(line)
    for item_id, lines in groups.items():
        if len(lines) > 1:
            title = items[item_id].catalogue_title or items[item_id].original_text
            for line in lines:
                flags.append(_flag("quote_line", line.line_id, "M4",
                                   f"{len(lines)} lines offer “{title}”. Keep one by excluding the others.", line.acknowledged))
    return flags


def quote_flags(quote: Quotation, quotes: list[Quotation]) -> list[ReviewFlag]:
    out: list[ReviewFlag] = []
    ack = quote.acknowledged

    def add(code: str, message: str) -> None:
        out.append(_flag("vendor", quote.quotation_id, code, message, ack))

    if quote.hidden_sheets:
        add("Q4", f"Hidden sheet(s) were ignored: {', '.join(quote.hidden_sheets)}.")
    if quote.uncached_formulas:
        add("Q5", "Some cells are formulas with no saved result, so their values could not be read.")
    if quote.read_from_image:
        add("Q6", "This file was read from an image, so values are less certain. Check the lines.")
    priced = [l for l in quote.lines if l.unit_price is not None]
    if quote.table_row_count >= 5 and len(quote.lines) < 0.6 * quote.table_row_count:
        add("Q13", f"The file has about {quote.table_row_count} table rows but only {len(quote.lines)} lines were read. Some may be missing.")
    if quote.stated_total is not None and priced:
        total = sum((l.line_total or (l.quantity or 0) * (l.price_per_unit or 0)) for l in priced if l.line_total or l.quantity)
        if total and not any(abs(quote.stated_total - total * m) <= total * m * Decimal("0.01")
                             for m in (Decimal(1), Decimal("1.05"), Decimal("1.12"), Decimal("1.18"), Decimal("1.28"))):
            add("Q17", "The total stated by the vendor does not match the sum of its lines.")
    currencies = {l.currency for l in quote.lines if l.currency}
    if AMBIGUOUS_DOLLAR in currencies or (priced and not currencies and not quote.currency):
        add("Q18", "The currency is unclear (a bare “$” or none stated). Confirm it before comparing.")
    elif len(currencies) > 1:
        add("Q18", f"Prices are in more than one currency ({', '.join(sorted(currencies))}).")
    if quote.tax_basis == "unclear" and priced and not any(l.tax_text for l in priced):
        add("Q23", "It is not clear whether prices include tax.")
    if quote.validity_text:
        if quote.validity_until is None:
            add("Q24", f"The validity “{quote.validity_text}” is not a date or period we can read.")
        elif quote.validity_until < date.today():
            add("Q24", f"This quotation expired on {quote.validity_until:%d %b %Y}.")
    if not quote.vendor_name:
        add("Q25", "The vendor's name could not be found, so the file name is used.")
    same = [q for q in active_quotes(quotes) if q.quotation_id != quote.quotation_id and vendor_key(q.vendor_name)
            and vendor_key(q.vendor_name) == vendor_key(quote.vendor_name)]
    if same:
        add("Q26", f"{quote.vendor_name} appears in more than one file. Keep one by excluding the other.")
    return out


def refresh(quote: Quotation, rfq: RFQ, quotes: list[Quotation], peers: dict | None = None) -> None:
    """Recompute every flag and the Review summary for one quotation."""
    if quote.status in ("rejected", "failed") or not quote.lines:   # no lines: still being read, nothing to check
        return
    peers = peers if peers is not None else peer_prices(quotes)
    for line in quote.lines:
        line.flags = [] if (line.excluded or quote.excluded) else line_flags(line, quote, rfq, peers)
    option_flags = [] if quote.excluded else _mark_options(quote, rfq)
    for flag in option_flags:
        line = next(l for l in quote.lines if l.line_id == flag.scope_id)
        line.flags = [f for f in line.flags if f.code != "M4"] + [flag]
    quote.flags = [] if quote.excluded else quote_flags(quote, quotes)
    all_flags = quote.flags + [f for l in quote.lines for f in l.flags]
    live = {quote.quotation_id} | {l.line_id for l in quote.lines if not l.excluded}
    quote.review_log = verifiers.sync_entries(quote.review_log, all_flags, live, BLOCKING)
    desired = "needs_review" if any(f.open and f.severity == "review" for f in all_flags) else "validated"
    if quote.status != desired and quote.status in ("parsed", "needs_review", "validated"):
        try:
            state.check_transition("quotation", quote.status, desired)
            quote.status = desired
        except state.InvalidTransition:
            pass


def refresh_all(quotes: list[Quotation], rfq: RFQ) -> None:
    peers = peer_prices(quotes)
    for q in quotes:
        refresh(q, rfq, quotes, peers)


def open_flags(quote: Quotation) -> list[ReviewFlag]:
    """Open issues, counting a group of options once rather than once per option line."""
    out, seen = [], set()
    for f in quote.flags + [f for l in quote.lines for f in l.flags]:
        if not (f.open and f.severity == "review"):
            continue
        key = (f.code, f.message) if f.code == "M4" else f.flag_id
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def eligible(line: QuotedLineItem) -> bool:
    """A line Phase 5 may calculate with: kept by the buyer, priced, matched, and with nothing left open."""
    return (not line.excluded and line.unit_price not in (None, 0) and line.matched_rfq_item_id is not None
            and line.match_status in ("matched", "possible") and not any(f.open for f in line.flags))


def injection_suspected(quote: Quotation) -> bool:
    """Q27 (info only): instruction-like text inside the document."""
    return any(_INJECTION.search(t) for t in quote.source_rows.values())
