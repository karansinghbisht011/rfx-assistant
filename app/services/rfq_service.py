"""Generate-an-RFQ workflow: G1 parse, catalogue search, G2 resolve, verifiers, save."""

import re
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from app import config, state
from app.schemas.llm import ResolveRequest
from app.schemas.rfq import RFQ, CatalogueCandidate, RequestedItem
from app.services import units, verifiers
from app.services.catalogue_service import Catalogue
from app.services.gemini_client import GeminiClient, RateLimited
from app.services.quantities import parse_quantity


@dataclass
class BuildResult:
    rfq: RFQ | None = None
    error: str | None = None
    unclear: bool = False  # the request itself could not be understood; show guidance with examples


STAGES = ("read", "match", "choose", "prepare")  # progress milestones reported to the UI
EXAMPLE_REQUEST = "4 pressure transmitters, 20 m instrument cable, 2 pairs of safety gloves"
NO_ITEMS_MESSAGE = "I couldn't find any products in that."


def initial_order(rfq: RFQ) -> list[str]:
    """Lines that need review first, confirmed lines last; original order kept within each group."""
    return [i.item_id for i in sorted(rfq.items, key=lambda item: not verifiers.needs_review(item))]


def ordered_items(rfq: RFQ) -> list[RequestedItem]:
    """Table order. Set once when the RFQ is built, so a line stays put while the buyer edits it."""
    position = {item_id: n for n, item_id in enumerate(rfq.display_order)}
    return sorted(rfq.items, key=lambda item: position.get(item.item_id, len(position)))


def search_phrase(item: RequestedItem) -> str:
    """The product words in a line, without its leading quantity and unit, for catalogue search."""
    words = item.original_text.split()
    while words and (re.fullmatch(r"[\d.,\-–/]+", words[0]) or units.normalize_unit(words[0]) or words[0].lower() in ("of", "a", "an")):
        words.pop(0)
    return " ".join(words) or item.original_text


def default_name(store: MutableMapping[str, Any]) -> str:
    """RFQ-YYYY-MM-DD, with a numeric suffix when the name is already used in this session (R19)."""
    base = f"RFQ-{date.today().isoformat()}"
    taken = {r.name for r in state.list_rfqs(store)}
    name, n = base, 2
    while name in taken:
        name, n = f"{base}-{n}", n + 1
    return name


def sanitize_name(name: str) -> str:
    """Safe for display and for use inside a filename."""
    cleaned = re.sub(r"[^A-Za-z0-9 _.\-]+", "", name).strip()
    return cleaned or "RFQ"


def build_draft(
    text: str,
    client: GeminiClient,
    catalogue: Catalogue,
    store: MutableMapping[str, Any],
    progress: Callable[[str], None] | None = None,
) -> BuildResult:
    def report(stage: str) -> None:
        if progress:
            progress(stage)

    problem = verifiers.check_input(text)
    if problem:
        return BuildResult(error=problem, unclear=True)
    if store.get("last_failed_input") == text:
        return BuildResult(error="Edit your request before trying again.")

    report("read")
    try:
        state.record_gemini_call(store)
        parsed = client.parse_request(text)
    except state.CallLimitReached:
        return BuildResult(error="The AI call limit for this session has been reached.")
    except RateLimited:
        return BuildResult(error="The AI service is busy right now (rate limit). Wait a minute, then try again.")
    except Exception:  # model or network failure: keep the buyer's text, allow a retry
        return BuildResult(error="Something went wrong reading your request. Please try again.")

    if len(parsed.items) > config.MAX_ITEMS:
        return BuildResult(error=f"That request has more than {config.MAX_ITEMS} items. Split it into smaller RFQs.")
    if parsed.input_class != "procurement_request" or not parsed.items:
        store["last_failed_input"] = text
        return BuildResult(error=NO_ITEMS_MESSAGE, unclear=True)

    report("match")
    items: list[RequestedItem] = []
    shortlists: dict[int, list[CatalogueCandidate]] = {}
    for index, p in enumerate(parsed.items):
        issues: list[str] = []
        if not verifiers.wording_in_input(p.original_text, text):
            issues.append("wording_unverified")
        quantity = None
        if p.quantity_text:
            if not verifiers.quantity_in_input(p.quantity_text, text):
                issues.append("quantity_unverified")
            else:
                result = parse_quantity(p.quantity_text)
                quantity = result.value
                if result.problem == "range":
                    issues.append("quantity_range")
        else:
            issues.append("quantity_unverified")
        unit = units.normalize_unit(p.unit_text)
        if p.unit_text and unit is None:
            issues.append("unit_unmapped")

        terms = [p.item_phrase, *p.search_terms]
        candidates = catalogue.shortlist(terms)
        status, winner = catalogue.decide(terms, candidates)
        shortlists[index] = candidates
        item = RequestedItem(
            original_text=p.original_text,
            quantity=quantity,
            unit=unit,
            unit_text=p.unit_text,
            match_status=status,
            match_candidates=candidates if status in ("ambiguous", "unmatched") else [],
            parse_issues=issues,
        )
        if winner:
            _apply_catalogue_item(item, winner)
        items.append(item)

    if all(i.match_status == "unmatched" for i in items) and not any(p.quantity_text for p in parsed.items):
        store["last_failed_input"] = text
        return BuildResult(error=NO_ITEMS_MESSAGE, unclear=True)

    if any(i.match_status == "ambiguous" for i in items):
        report("choose")
    _resolve_unclear(items, parsed, shortlists, client, store)
    report("prepare")
    for item in items:
        if item.unit is None and item.catalogue_code and not item.unit_text:
            entry = catalogue.by_code(item.catalogue_code)
            if entry:
                item.unit, item.unit_suggested = entry.default_unit, True  # shown as a suggestion (R9)

    rfq = RFQ(name=default_name(store), items=items, source_session_id=store.get("session_id", ""))
    rfq.flags = verifiers.rfq_level_flags(len(items), text)
    verifiers.refresh_flags(rfq)
    rfq.display_order = initial_order(rfq)
    store["last_failed_input"] = None
    return BuildResult(rfq=rfq)


def _apply_catalogue_item(item: RequestedItem, candidate: CatalogueCandidate, *, by_buyer: bool = False) -> None:
    item.catalogue_code = candidate.code
    item.catalogue_title = candidate.title
    item.buyer_selected = by_buyer


def _resolve_unclear(items, parsed, shortlists, client, store) -> None:
    """G2: only for ambiguous items. A pick outside the shortlist is rejected (R11); only a
    high-confidence pick is applied, otherwise the model's suggestion just moves to the top."""
    pending = [
        ResolveRequest(
            item_index=i,
            original_text=parsed.items[i].original_text,
            item_phrase=parsed.items[i].item_phrase,
            candidates=shortlists[i],
        )
        for i, item in enumerate(items)
        if item.match_status == "ambiguous"
    ]
    if not pending:
        return
    try:
        state.record_gemini_call(store)
        result = client.resolve_items(pending)
    except Exception:  # fall back to the buyer's picker
        return
    for resolution in result.resolutions:
        item = items[resolution.item_index]
        valid = {c.code: c for c in shortlists[resolution.item_index]}
        if resolution.choice_code not in valid:
            continue
        choice = valid[resolution.choice_code]
        best = max(c.score for c in valid.values())
        # A confident AI pick that the word match does not support (for example "Anchor bolts" for
        # "hex bolts") stays a suggestion for the buyer instead of being applied.
        if resolution.confidence == "high" and choice.score >= best - config.MATCH_PICK_TOLERANCE:
            item.match_status = "fuzzy"
            item.match_candidates = []
            _apply_catalogue_item(item, choice)
        else:
            item.match_candidates = [choice, *[c for c in item.match_candidates if c.code != choice.code]]


def pick_catalogue_item(rfq: RFQ, item_id: str, candidate: CatalogueCandidate) -> None:
    """The buyer chose a catalogue item. Suggest its default unit only if the line has no unit."""
    item = next(i for i in rfq.items if i.item_id == item_id)
    _apply_catalogue_item(item, candidate, by_buyer=True)
    item.match_status = "exact"
    item.match_candidates = []
    if item.unit is None or item.unit_suggested:
        item.unit, item.unit_suggested = candidate.default_unit, True
    verifiers.refresh_flags(rfq)


def set_quantity(rfq: RFQ, item_id: str, value) -> None:
    item = next(i for i in rfq.items if i.item_id == item_id)
    item.quantity = verifiers.quantity_to_decimal(value)
    item.parse_issues = [p for p in item.parse_issues if not p.startswith("quantity_")]
    verifiers.refresh_flags(rfq)


def set_unit(rfq: RFQ, item_id: str, unit: str | None) -> None:
    item = next(i for i in rfq.items if i.item_id == item_id)
    item.unit, item.unit_suggested = unit, False
    item.parse_issues = [p for p in item.parse_issues if p != "unit_unmapped"]
    verifiers.refresh_flags(rfq)


def acknowledge(rfq: RFQ, item_id: str | None, code: str) -> None:
    """Accept a flag as it is. RFQ-level flags are accepted by clearing them."""
    if item_id is None or item_id == "rfq":
        for flag in rfq.flags:
            if flag.code == code:
                flag.resolution = "accepted"
        verifiers.refresh_flags(rfq)
        return
    item = next(i for i in rfq.items if i.item_id == item_id)
    if code in verifiers.ACCEPTABLE_CODES and code not in item.acknowledged:
        item.acknowledged.append(code)
    verifiers.refresh_flags(rfq)


def remove_item(rfq: RFQ, item_id: str) -> None:
    rfq.items = [i for i in rfq.items if i.item_id != item_id]
    verifiers.refresh_flags(rfq)


def finalize(store: MutableMapping[str, Any], rfq: RFQ) -> RFQ:
    """Save the reviewed RFQ for this session. Refuses while anything is unresolved."""
    if not verifiers.can_save(rfq):
        raise ValueError("Resolve or accept every item in the Review summary before saving.")
    rfq.name = sanitize_name(rfq.name)
    if rfq.name in {r.name for r in state.list_rfqs(store)}:
        rfq.name = default_name(store) if rfq.name.startswith("RFQ-") else f"{rfq.name}-2"
    state.check_transition("rfq", rfq.status, "ready")
    rfq.status = "ready"
    return state.save_rfq(store, rfq)
