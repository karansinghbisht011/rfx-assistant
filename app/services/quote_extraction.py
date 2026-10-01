"""Call G3 on a parsed document and turn the verbatim answer into a Quotation's fields."""

from collections import Counter
from collections.abc import Callable

from app import config
from app.schemas.llm import WireExtractedQuote
from app.schemas.quotation import Charge, Quotation, QuotedLineItem
from app.services import units
from app.services.document_ingestion import ParsedDocument
from app.services.gemini_client import GeminiClient
from app.services.quote_parsing import (
    AMBIGUOUS_DOLLAR, detect_currency, detect_tax_basis, parse_amount, parse_basis, parse_date_text,
    parse_quote_quantity, parse_validity,
)

CHUNK_ROWS = 200       # larger documents are read in row-numbered chunks so one answer never runs out of room
CONTEXT_ROWS = 12      # the top of the document (vendor, terms) is repeated in every chunk


def extract(client: GeminiClient, doc: ParsedDocument, pdf_bytes: bytes | None, record_call: Callable[[], None],
            on_line: Callable[[dict], None] | None = None) -> WireExtractedQuote:
    """One call (or one per chunk for very large files). record_call counts each against the session cap."""
    if doc.read_from_image:
        record_call()
        return client.extract_quote("", pdf_bytes, on_line)
    rows = doc.rows
    if len(rows) <= CHUNK_ROWS:
        record_call()
        return client.extract_quote(doc.as_text(), None, on_line)
    head = rows[:CONTEXT_ROWS]
    parts: list[WireExtractedQuote] = []
    for start in range(CONTEXT_ROWS, len(rows), CHUNK_ROWS):
        chunk = head + rows[start:start + CHUNK_ROWS]
        record_call()
        parts.append(client.extract_quote("\n".join(f"[{r.ref}] {r.text}" for r in chunk), None, on_line))
    merged = parts[0].model_copy(deep=True)
    seen = {(l.ref, l.desc) for l in merged.lines}
    for part in parts[1:]:
        merged.lines += [l for l in part.lines if (l.ref, l.desc) not in seen]
        merged.charges = (merged.charges or []) + (part.charges or [])
        merged.warnings = (merged.warnings or []) + (part.warnings or [])
        merged.is_quotation = merged.is_quotation or part.is_quotation
        for name in ("vendor", "quote_ref", "date", "revision", "validity", "payment", "delivery", "total"):
            if getattr(merged, name) is None:
                setattr(merged, name, getattr(part, name))
    return merged


def _text(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def apply_extraction(quote: Quotation, wire: WireExtractedQuote, document_text: str) -> None:
    """Fill the Quotation from the extraction. Every value is parsed from the text as written; none is invented."""
    quote.vendor_name = _text(wire.vendor)
    quote.quote_reference = _text(wire.quote_ref)
    quote.revision = _text(wire.revision)
    quote.quote_date_text = _text(wire.date)
    quote.quote_date = parse_date_text(quote.quote_date_text)
    quote.validity_text = _text(wire.validity)
    quote.validity_until = parse_validity(quote.validity_text, quote.quote_date)
    quote.payment_terms = _text(wire.payment)
    quote.delivery_terms = _text(wire.delivery)
    quote.stated_total_text = _text(wire.total)
    quote.stated_total = parse_amount(quote.stated_total_text)
    quote.charges = [Charge(kind=c.kind, scope=c.scope, text=c.text, row_ref=c.ref) for c in (wire.charges or [])]

    document_currencies = {c for c in (detect_currency(w) for w in document_text.splitlines()) if c and c != AMBIGUOUS_DOLLAR}
    lines: list[QuotedLineItem] = []
    for wl in wire.lines:
        price = parse_amount(wl.price)
        basis = parse_basis(wl.basis, wl.price)
        line = QuotedLineItem(
            row_ref=wl.ref,
            # a table row is its own evidence; the model quotes words only for rows holding several lines
            source_quote=_text(wl.src) or quote.source_rows.get(wl.ref, ""),
            source_description=wl.desc.strip(),
            quantity_text=wl.qty, unit_text=_text(wl.unit), unit_price_text=_text(wl.price),
            price_basis_text=_text(wl.basis), line_total_text=_text(wl.total),
            currency_text=_text(wl.cur), tax_text=_text(wl.tax),
            moq_text=_text(wl.moq), option_label=_text(wl.opt), remarks=_text(wl.note),
            quantity=parse_quote_quantity(wl.qty), unit_price=price,
            unit=units.normalize_unit(wl.unit, quote_side=True) if wl.unit else None,
            price_basis_quantity=basis.quantity if (basis.recognised or wl.basis is None) else None,
            line_total=parse_amount(wl.total), moq=parse_amount(wl.moq),
            currency=detect_currency(wl.cur, wl.price),
        )
        if line.price_basis_text and not basis.recognised:
            line.price_basis_quantity = None
        lines.append(line)
    if len(document_currencies) == 1:  # one currency stated for the whole document: lines inherit it
        only = next(iter(document_currencies))
        for line in lines:
            if line.currency is None and line.unit_price is not None:
                line.currency = only
    quote.lines = lines
    counts = Counter(l.currency for l in lines if l.currency)
    quote.currency = counts.most_common(1)[0][0] if counts else None
    tax_texts = [l.tax_text for l in lines if l.tax_text] + [c.text for c in quote.charges if c.kind == "tax"]
    tax_rows = [t for t in document_text.splitlines() if "gst" in t.lower() or "tax" in t.lower()]
    basis = detect_tax_basis(*tax_texts, *tax_rows)
    says_included = any("includ" in t.lower() or "incl" in t.lower().split() for t in tax_texts + tax_rows)
    if basis == "unclear" and not says_included and any(c.kind == "tax" and c.scope == "quote" for c in quote.charges):
        basis = "exclusive"  # a tax amount listed as its own row is added on top of the prices
    quote.tax_basis = basis  # type: ignore[assignment]
    quote.notes = list(wire.warnings or [])
