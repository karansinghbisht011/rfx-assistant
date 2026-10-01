"""Match vendor lines to RFQ items: code first, Gemini (G4) only for lines code cannot place confidently."""

import re
from collections.abc import MutableMapping
from typing import Any

from rapidfuzz import fuzz

from app import config, state
from app.schemas.quotation import Quotation, QuotedLineItem
from app.schemas.rfq import RFQ, RequestedItem
from app.services import rfq_service
from app.services.catalogue_service import fold
from app.services.gemini_client import GeminiClient


def _titles(item: RequestedItem) -> list[str]:
    return [t for t in (item.catalogue_title, rfq_service.search_phrase(item)) if t]


def line_text(line: QuotedLineItem) -> str:
    return line.source_description or line.source_quote


def score(description: str, item: RequestedItem) -> float:
    d = fold(description)
    return max((fuzz.token_set_ratio(d, fold(t)) for t in _titles(item)), default=0.0)


def spec_tokens(item: RequestedItem) -> set[str]:
    """Numbers in the buyer's wording (sizes, ratings) that a vendor line should also mention."""
    return set(re.findall(r"\d+(?:\.\d+)?", rfq_service.search_phrase(item)))


_OPTIONAL = re.compile(r"\boptional\b|\brecommended\b|not included in (the )?total", re.I)


def is_optional(line: QuotedLineItem) -> bool:
    """The vendor itself marks the line as an optional or recommended extra, outside its offer."""
    return bool(_OPTIONAL.search(" ".join(t for t in (line.option_label, line.remarks) if t)))


_NOT_STATED = re.compile(r"\b(missing|not (specified|stated|given|mentioned|provided)|unspecified|no .* (stated|given))\b", re.I)


def real_differences(differences: list[str]) -> list[str]:
    """A detail the vendor simply did not write is not a difference from the RFQ; a conflicting one is."""
    return [d for d in differences if not _NOT_STATED.search(d)]


def code_first(quote: Quotation, rfq: RFQ) -> list[QuotedLineItem]:
    """Match the clear lines by code and return the lines that still need a decision."""
    unresolved = []
    for line in quote.lines:
        if is_optional(line):  # an optional extra is never matched to an RFQ item
            line.match_status, line.match_reason = "extra", "Optional item offered by the vendor"
            continue
        ranked = sorted(((score(line_text(line), item), item) for item in rfq.items), key=lambda p: p[0], reverse=True)
        if not ranked:
            unresolved.append(line)
            continue
        top, item = ranked[0]
        second = ranked[1][0] if len(ranked) > 1 else 0.0
        specs = spec_tokens(item)
        stated = re.findall(r"\d+(?:\.\d+)?", line_text(line))
        # the vendor line must carry the RFQ's sizes and ratings, or at least not state different ones
        covered = all(tok in stated for tok in specs) or not stated
        line.match_score = round(top, 1)
        if top >= config.MATCH_LINE_HIGH and top - second >= config.MATCH_LINE_MARGIN and covered:
            line.matched_rfq_item_id, line.match_status, line.match_reason = item.item_id, "matched", "Same product"
        else:
            unresolved.append(line)
    return unresolved


def _rfq_payload(rfq: RFQ) -> list[dict]:
    return [
        {"id": i.item_id, "title": i.catalogue_title or i.original_text, "buyer_wording": i.original_text,
         "quantity": str(i.quantity) if i.quantity is not None else None, "unit": i.unit}
        for i in rfq.items
    ]


def ai_pass(client: GeminiClient, store: MutableMapping[str, Any], quote: Quotation, rfq: RFQ,
            lines: list[QuotedLineItem]) -> None:
    """G4 for the unresolved lines. A confident 'matched' that the wording does not support is downgraded."""
    if not lines:
        return
    state.record_gemini_call(store)
    payload = [{"line_id": l.line_id, "description": line_text(l), "unit": l.unit_text} for l in lines]
    result = client.match_lines(_rfq_payload(rfq), payload)
    by_id = {l.line_id: l for l in lines}
    items = {i.item_id: i for i in rfq.items}
    for m in result.matches:
        line = by_id.get(m.line_id)
        if line is None:
            continue
        item = items.get(m.rfq_item_id) if m.rfq_item_id else None
        differences = real_differences(m.differences)
        line.match_reason, line.match_differences, line.is_alternate = m.reason, differences, m.is_alternate
        if item is None:  # M1: an id that is not on the RFQ is never accepted
            line.matched_rfq_item_id, line.match_status = None, "extra" if m.status == "extra" else "no_match"
            continue
        line.matched_rfq_item_id = item.item_id
        line.match_score = round(score(line_text(line), item), 1)
        status = m.status
        if status == "matched" and (differences or line.match_score < config.MATCH_LINE_LOW):  # M2/M3
            status = "possible"
        line.match_status = status


def match_quote(client: GeminiClient, store: MutableMapping[str, Any], quote: Quotation, rfq: RFQ) -> None:
    ai_pass(client, store, quote, rfq, code_first(quote, rfq))
