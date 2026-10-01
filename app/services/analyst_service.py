"""The analyst: the buyer's request is read by the model as rules, and code builds the purchase proposal from them.

The model never writes a figure. It sees the RFQ, every offer and the existing summaries as data, and returns rules
(`ProposalSpec`) and a short reply. Code validates the rules against real ids, finds the cheapest purchase that keeps
them (allocation.py), computes every number, checks the rules against the result, and writes the rule report itself.
"""

import json
import re
from collections.abc import MutableMapping
from decimal import Decimal
from typing import Any

from app import config, state
from app.schemas.analysis import Assumptions
from app.schemas.analyst import AnalystTurn, Pin, Proposal, ProposalRow, ProposalSpec, RuleResult
from app.schemas.llm import WireProposal
from app.schemas.quotation import Quotation
from app.schemas.rfq import RFQ
from app.services import allocation, comparison
from app.services.gemini_client import BadResponse, GeminiClient, GeminiError, NotConfigured, RateLimited

NEUTRAL_REPLY = "I have read your request and built the proposal below from the rules shown."
AWARD_WORDING = re.compile(r"\baward(ed|ing|s)?\b|recommend(s|ed)?\s+(buying|ordering|purchasing|placing)|you should (buy|order|purchase)", re.I)
ALIAS = re.compile(r"\b[VI]\d{1,3}\b")


class Aliases:
    """Short ids for the model (V1, I2), so no long id is ever echoed and an unknown id is easy to spot."""

    def __init__(self, rfq: RFQ, quotes: list[Quotation]):
        self.vendors = {f"V{n}": q.quotation_id for n, q in enumerate(quotes, start=1)}
        self.items = {f"I{n}": i.item_id for n, i in enumerate(rfq.items, start=1)}
        self.vendor_alias = {v: k for k, v in self.vendors.items()}
        self.item_alias = {v: k for k, v in self.items.items()}
        self.vendor_name = {q.quotation_id: q.display_name for q in quotes}
        self.item_name = {i.item_id: i.catalogue_title or i.original_text for i in rfq.items}

    def names_in(self, text: str) -> str:
        """Replace ids the model wrote (V2, I3) with names; an id we never gave it is dropped."""
        def swap(m: re.Match) -> str:
            real = self.vendors.get(m.group(0)) or self.items.get(m.group(0))
            return (self.vendor_name.get(real) or self.item_name.get(real) or "") if real else ""
        return re.sub(r"\s{2,}", " ", ALIAS.sub(swap, text)).strip()


def _num(value: Decimal | None) -> float | None:
    return None if value is None else float(round(value, 2))


def build_context(rfq: RFQ, quotes: list[Quotation], aliases: Aliases, rates: dict[str, Decimal],
                  summaries: comparison.Analysis) -> dict[str, Any]:
    """Everything the model may use, as plain structured data. Offers include lines still under review (marked)."""
    wide = comparison.analyse(rfq, quotes, Assumptions(include_flagged=True), rates)
    vendors = [{
        "id": aliases.vendor_alias[q.quotation_id], "name": q.display_name, "file": q.source_filename, "currency": q.currency,
        "prices_include_tax": {"inclusive": "yes", "exclusive": "no"}.get(q.tax_basis, "unclear"),
        "validity": q.validity_text, "payment": q.payment_terms, "delivery": q.delivery_terms,
        "stated_charges": [f"{c.kind}: {c.text}"[:120] for c in q.charges if c.scope == "quote"][:6],
        "open_review_points": sum(1 for e in q.review_log if e.status == "open"),
    } for q in quotes]
    offers = [{
        "vendor": aliases.vendor_alias[o.vendor_id], "item": aliases.item_alias[o.item_id], "unit_price_inr": _num(o.unit_base),
        "quoted_as": o.quoted_price[:40], "quoted_qty": _num(o.quoted_qty), "min_order": _num(o.moq), "under_review": o.flagged,
    } for o in wide.offers if o.cost_base is not None]
    left_out = [{"vendor": aliases.vendor_alias[e.vendor_id], "why": e.code, "line": e.message[:90]}
                for e in wide.exclusions if e.code != "option"][:40]
    data = {
        "rfq": {"name": rfq.name, "items": [{
            "id": aliases.item_alias[i.item_id], "buyer_wording": i.original_text, "catalogue_item": i.catalogue_title,
            "required_qty": _num(i.quantity), "unit": i.unit} for i in rfq.items]},
        "vendors": vendors, "offers": offers, "left_out_lines": left_out,
        "summaries": {
            "lowest_offer_per_item": [{"item": aliases.item_alias[i], "vendor": aliases.vendor_alias[low[0].vendor_id],
                                       "unit_price_inr": _num(low[0].unit_base), "cost_inr": _num(low[0].cost_base)}
                                      for i, low in summaries.lowest.items()],
            "vendor_totals": [{"vendor": aliases.vendor_alias[s.vendor_ids[0]], "covers_all_items": s.complete, "total_inr": _num(s.total)}
                              for s in summaries.singles],
        },
        "basis": f"prices per RFQ unit, before tax, in {config.COMPARISON_CURRENCY}; cost = unit price x required quantity",
    }
    while len(json.dumps(data)) > config.ANALYST_CONTEXT_MAX_CHARS and data["left_out_lines"]:
        data["left_out_lines"] = data["left_out_lines"][: len(data["left_out_lines"]) // 2]
    return data


# ----------------------------------------------------------------------------- the model's rules, checked
class BadRules(ValueError):
    pass


def to_spec(wire: WireProposal, aliases: Aliases) -> ProposalSpec:
    """Rules from the model. Every id must be one we gave it; anything else is rejected, never guessed."""
    def vendor(tag: str) -> str:
        if tag not in aliases.vendors:
            raise BadRules(f"“{tag}” is not a vendor id in the data.")
        return aliases.vendors[tag]

    def item(tag: str) -> str:
        if tag not in aliases.items:
            raise BadRules(f"“{tag}” is not an item id in the data.")
        return aliases.items[tag]

    try:
        return ProposalSpec(
            allow_split=wire.allow_split, every_vendor_supplies=wire.every_vendor_supplies,
            min_items_per_vendor=wire.min_items_per_vendor, max_vendors=wire.max_vendors,
            require_vendor_ids=[vendor(t) for t in wire.require_vendors or []],
            leave_out_vendor_ids=[vendor(t) for t in wire.leave_out_vendors or []],
            pins=[Pin(item_id=item(p.item), vendor_id=vendor(p.vendor), quantity=Decimal(p.quantity) if p.quantity else None)
                  for p in wire.pins or []],
            include_flagged=wire.include_flagged, assume_rfq_unit=wire.assume_rfq_unit)
    except BadRules:
        raise
    except ValueError as exc:
        raise BadRules("A rule value is out of range.") from exc


def spec_to_wire(spec: ProposalSpec, aliases: Aliases) -> dict:
    return {
        "allow_split": spec.allow_split, "every_vendor_supplies": spec.every_vendor_supplies,
        "min_items_per_vendor": spec.min_items_per_vendor, "max_vendors": spec.max_vendors,
        "require_vendors": [aliases.vendor_alias[v] for v in spec.require_vendor_ids if v in aliases.vendor_alias],
        "leave_out_vendors": [aliases.vendor_alias[v] for v in spec.leave_out_vendor_ids if v in aliases.vendor_alias],
        "pins": [{"item": aliases.item_alias[p.item_id], "vendor": aliases.vendor_alias[p.vendor_id],
                  "quantity": int(p.quantity) if p.quantity else None}
                 for p in spec.pins if p.item_id in aliases.item_alias and p.vendor_id in aliases.vendor_alias],
        "include_flagged": spec.include_flagged, "assume_rfq_unit": spec.assume_rfq_unit,
    }


def clean_reply(reply: str, question: str, aliases: Aliases) -> str:
    """The model's words, with ids turned into names. A reply that carries figures of its own, or award wording, is replaced."""
    text = aliases.names_in(reply or "").strip()
    allowed = set(re.findall(r"\d+", question))
    if not text or AWARD_WORDING.search(text) or any(d not in allowed for d in re.findall(r"\d+", text)):
        return NEUTRAL_REPLY
    return text[:400]


# ----------------------------------------------------------------------------- the proposal, built by code
def build_proposal(rfq: RFQ, quotes: list[Quotation], spec: ProposalSpec, rates: dict[str, Decimal]) -> Proposal:
    base = config.COMPARISON_CURRENCY
    assumptions = Assumptions(exclude_vendor_ids=spec.leave_out_vendor_ids, include_flagged=spec.include_flagged,
                              use_rfq_unit_for_missing=spec.assume_rfq_unit)
    analysis = comparison.analyse(rfq, quotes, assumptions, rates)
    ranked = comparison.ranked(analysis.offers)
    can_supply = {o.vendor_id for o in ranked}
    required = set(spec.require_vendor_ids) - set(spec.leave_out_vendor_ids)
    if spec.every_vendor_supplies:
        required |= can_supply
    rules = allocation.Rules(
        allow_split=spec.allow_split, min_items_per_vendor=spec.min_items_per_vendor or 0, required=required,
        max_vendors=spec.max_vendors, pins=[(p.item_id, p.vendor_id, p.quantity) for p in spec.pins])
    alloc = allocation.solve(rfq.items, ranked, rules)
    free = allocation.solve(rfq.items, ranked, allocation.Rules(allow_split=True))

    items = {i.item_id: i for i in rfq.items}
    order = {i.item_id: n for n, i in enumerate(rfq.items)}
    rows = [ProposalRow(
        item_id=s.item_id, item=items[s.item_id].catalogue_title or items[s.item_id].original_text,
        unit=items[s.item_id].unit or "", required_qty=items[s.item_id].quantity or Decimal(0),
        vendor_id=s.vendor_id, vendor=s.offer.vendor, quantity=s.quantity, unit_price=comparison.money(s.offer.unit_base),  # type: ignore[arg-type]
        quoted_price=s.offer.quoted_price, quoted_currency=s.offer.currency, total=comparison.money(s.total))
        for s in sorted(alloc.shares, key=lambda s: (order[s.item_id], s.offer.vendor))]
    complete = [s for s in analysis.singles if s.complete]
    proposal = Proposal(
        rows=rows, grand_total=comparison.money(alloc.total) if rows else None, currency=base,
        cheapest_possible_total=comparison.money(free.total) if free.shares else None,
        best_single=(complete[0].label, complete[0].total) if complete and complete[0].total is not None else None,
        feasible=alloc.feasible, unfilled=[items[i].catalogue_title or items[i].original_text for i in alloc.unfilled])
    proposal.rules = _report(spec, alloc, rows, analysis.vendors, items, can_supply)
    proposal.caveats = _caveats(alloc, rates, base)
    return proposal


def _report(spec: ProposalSpec, alloc: allocation.Allocation, rows: list[ProposalRow], names: dict[str, str],
            items: dict, can_supply: set[str]) -> list[RuleResult]:
    """What the rules came to, checked against the actual purchase (never taken from the model or the solver)."""
    used: dict[str, set[str]] = {}
    for r in rows:
        used.setdefault(r.vendor_id, set()).add(r.item_id)
    unmet = dict(alloc.unmet)
    out: list[RuleResult] = []
    if spec.allow_split:
        split = sorted({r.item for r in rows if sum(1 for x in rows if x.item_id == r.item_id) > 1})
        out.append(RuleResult(text="Split purchases allowed", met=True, detail=("Split: " + ", ".join(split)) if split else "None needed"))
    else:
        out.append(RuleResult(text="Each item bought whole from one vendor", met=True))
    if spec.every_vendor_supplies:
        missing = [names[v] for v in names if v not in used]
        silent = [names[v] for v in names if v not in can_supply]
        detail = ""
        if silent:
            detail = "No comparable offer from " + ", ".join(silent) + "."
        elif missing:
            detail = unmet.get("required") or "Could not include " + ", ".join(missing) + "."
        out.append(RuleResult(text="Every vendor supplies at least one item", met=not missing, detail=detail))
    for v in spec.require_vendor_ids:
        out.append(RuleResult(text=f"{names.get(v, 'The vendor')} supplies", met=v in used,
                              detail="" if v in used else unmet.get("required", "No comparable offer.")))
    if spec.leave_out_vendor_ids:
        out.append(RuleResult(text="Left out: " + ", ".join(names.get(v) or "a vendor" for v in spec.leave_out_vendor_ids), met=True))
    if spec.min_items_per_vendor:
        ok = all(len(s) >= spec.min_items_per_vendor for s in used.values())
        out.append(RuleResult(text=f"Each vendor used supplies at least {spec.min_items_per_vendor} items", met=ok,
                              detail="" if ok else unmet.get("min_items", "")))
    if spec.max_vendors:
        ok = len(used) <= spec.max_vendors
        out.append(RuleResult(text=f"At most {spec.max_vendors} vendors", met=ok, detail="" if ok else unmet.get("max_vendors", "")))
    for p in spec.pins:
        got = sum(r.quantity for r in rows if r.item_id == p.item_id and r.vendor_id == p.vendor_id)
        ok = got == (p.quantity if p.quantity else (items[p.item_id].quantity or Decimal(0)))
        title = items[p.item_id].catalogue_title or items[p.item_id].original_text
        who = f"{p.quantity:g} from " if p.quantity else ""
        out.append(RuleResult(text=f"{title}: {who}{names.get(p.vendor_id, 'the vendor')}", met=ok, detail="" if ok else unmet.get("pins", "")))
    if spec.include_flagged:
        n = sum(1 for s in alloc.shares if s.offer.flagged)
        out.append(RuleResult(text="Lines still under review included", met=True, detail=f"{n} used" if n else "None needed"))
    if spec.assume_rfq_unit:
        out.append(RuleResult(text="Your RFQ unit assumed where none is stated", met=True))
    return out


def _caveats(alloc: allocation.Allocation, rates: dict[str, Decimal], base: str) -> list[str]:
    out = ["Unit prices are taken as flat: no volume discounts are assumed when an item is split."]
    used = list({(s.vendor_id, s.item_id): s.offer for s in alloc.shares}.values())
    for currency in sorted({o.currency for o in used if o.currency != base}):
        rate = rates.get(currency)
        out.append(f"{currency} prices are converted at {rate:g} {base} per {currency}.")
    taken = sorted({n for o in used for n in o.notes if "taken out" in n})
    if taken:
        out.append("Tax-inclusive prices have the stated tax taken out (" + "; ".join(taken) + ").")
    if any(o.flagged for o in used):
        out.append("Some lines used are still under review in the Review step.")
    if any(o.moq and o.moq > o.rfq_quantity for o in used):
        out.append("A vendor's minimum order is larger than the quantity needed; the needed quantity is used.")
    if alloc.unfilled:
        out.append("Items nobody could supply are listed as not priced.")
    out += [f"Not kept: {reason}" for _, reason in alloc.unmet]
    return out


# ----------------------------------------------------------------------------- one turn
def _failed(question: str, message: str) -> AnalystTurn:
    return AnalystTurn(question=question, status="failed", reply=message)


def run_turn(store: MutableMapping[str, Any], rfq: RFQ, quotes: list[Quotation], question: str, client: GeminiClient,
             rates: dict[str, Decimal], history: list[AnalystTurn]) -> AnalystTurn:
    """Answer one request. Never raises: every problem becomes a turn the buyer can read."""
    question = " ".join(re.sub(r"[<>]", " ", question or "").split())
    if not question:
        return _failed(question, "Type what you would like the proposal to do.")
    if len(question) > config.ANALYST_MAX_QUESTION_CHARS:
        return _failed(question[: config.ANALYST_MAX_QUESTION_CHARS], f"Please keep the request under {config.ANALYST_MAX_QUESTION_CHARS} characters.")
    if not quotes:
        return _failed(question, "Keep at least one quotation in Review first.")
    aliases = Aliases(rfq, quotes)
    data = json.dumps(build_context(rfq, quotes, aliases, rates, comparison.analyse(rfq, quotes, Assumptions(), rates)),
                      ensure_ascii=False, separators=(",", ":"))
    past = [{"request": t.question, "reply": t.reply, "status": t.status} for t in history[-config.ANALYST_HISTORY_TURNS:]]
    last = next((t.spec for t in reversed(history) if t.spec is not None), None)
    previous = spec_to_wire(last, aliases) if last else None
    correction = None
    try:
        for _ in range(2):
            state.record_gemini_call(store)
            wire = client.propose(data, question, past, previous, correction)
            try:
                spec = to_spec(wire, aliases)
                break
            except BadRules as exc:
                correction = str(exc)
        else:
            return _failed(question, "I could not turn that into a valid set of rules. Try rephrasing it.")
    except state.CallLimitReached:
        return _failed(question, "The AI call limit for this session has been reached.")
    except RateLimited:
        return _failed(question, "The AI service is busy (rate limit). Try again in a minute.")
    except NotConfigured as exc:
        return _failed(question, str(exc))
    except (BadResponse, GeminiError):
        return _failed(question, "The analyst could not answer that. Try again.")
    if wire.unsupported:
        return AnalystTurn(question=question, status="unsupported", reply=aliases.names_in(wire.unsupported)[:300])
    if wire.clarifying_question:
        return AnalystTurn(question=question, status="clarify", reply=aliases.names_in(wire.clarifying_question)[:300])
    proposal = build_proposal(rfq, quotes, spec, rates)
    return AnalystTurn(question=question, reply=clean_reply(wire.reply, question, aliases), spec=spec, proposal=proposal)
