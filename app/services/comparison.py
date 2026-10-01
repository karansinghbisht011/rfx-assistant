"""Deterministic comparison of vendor offers against an RFQ. No AI, no network: pure functions over the session data.

Basis: unit price x RFQ quantity, excluding tax, in the comparison currency. Every line that is left out of a
ranking is listed with its reason, so reconciliation is exact: eligible offers plus exclusions equals all lines.
"""

import itertools
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app import config
from app.schemas.analysis import Assumptions
from app.schemas.quotation import Quotation, QuotedLineItem
from app.schemas.rfq import RFQ, RequestedItem
from app.services import units
from app.services.quote_parsing import detect_tax_basis

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Offer:
    vendor_id: str
    vendor: str
    item_id: str
    line_id: str
    unit_price: Decimal            # per RFQ unit, excluding tax, in the quoted currency
    currency: str
    cost: Decimal                  # unit_price x RFQ quantity, quoted currency
    cost_base: Decimal | None      # the same in the comparison currency; None without a rate
    flagged: bool = False          # an open review flag was set aside by "include flagged lines"
    notes: tuple[str, ...] = ()
    quoted_qty: Decimal | None = None   # what the vendor quoted for, in RFQ units
    moq: Decimal | None = None          # the vendor's minimum order, in RFQ units
    quoted_price: str = ""              # the price as the vendor wrote it, for display

    @property
    def rfq_quantity(self) -> Decimal:
        return self.cost / self.unit_price if self.unit_price else Decimal(0)

    @property
    def unit_base(self) -> Decimal | None:
        """Price per RFQ unit in the comparison currency."""
        return self.cost_base / self.rfq_quantity if self.cost_base is not None and self.rfq_quantity else None


@dataclass(frozen=True)
class Exclusion:
    vendor_id: str
    vendor: str
    line_id: str | None
    item_id: str | None
    code: str                      # excluded, unpriced, unmatched, flagged, unit, tax, currency, option
    message: str


@dataclass
class Scenario:
    kind: str                      # single_vendor or hybrid
    label: str
    complete: bool
    total: Decimal | None          # comparison currency
    covered: int
    allocations: dict[str, Offer] = field(default_factory=dict)   # item_id -> offer
    missing_item_ids: list[str] = field(default_factory=list)
    vendor_ids: list[str] = field(default_factory=list)


@dataclass
class Analysis:
    rfq_id: str
    base_currency: str
    assumptions: Assumptions
    offers: list[Offer]
    exclusions: list[Exclusion]
    vendors: dict[str, str]                                   # vendor_id -> name
    lowest: dict[str, list[Offer]]                            # item_id -> tied lowest offers (usually one)
    singles: list[Scenario]
    hybrid: Scenario
    unconverted_currencies: set[str]
    notes: list[str]
    line_count: int

    def reconciles(self) -> bool:
        """C1: every line of every compared quotation is either an offer or listed with a reason."""
        return len(self.offers) + len(self.exclusions) == self.line_count


def _percent(text: str | None) -> Decimal | None:
    found = {m for m in re.findall(r"(\d+(?:\.\d+)?)\s*%", text or "")}
    return Decimal(next(iter(found))) if len(found) == 1 else None


def tax_rate(line: QuotedLineItem, quote: Quotation) -> Decimal | None:
    """A GST/tax percentage stated for the line, or the single one stated anywhere on the quotation."""
    own = _percent(line.tax_text)
    if own is not None:
        return own
    texts = [c.text for c in quote.charges if c.kind == "tax"]
    texts += [t for t in quote.source_rows.values() if re.search(r"gst|tax", t, re.I)]
    rates = {r for r in (_percent(t) for t in texts) if r is not None}
    return next(iter(rates)) if len(rates) == 1 else None


def line_tax_basis(line: QuotedLineItem, quote: Quotation) -> str:
    own = detect_tax_basis(line.tax_text) if line.tax_text else "unclear"
    return own if own != "unclear" else quote.tax_basis


def _open(line: QuotedLineItem) -> bool:
    return any(f.open and f.severity != "info" for f in line.flags)


def unit_factor(line: QuotedLineItem, item: RequestedItem, a: Assumptions) -> tuple[Decimal | None, str | None]:
    """RFQ units in one of the vendor's units, or why that cannot be known."""
    if not item.unit:
        return Decimal(1), None
    if not line.unit:
        return (Decimal(1), None) if a.use_rfq_unit_for_missing else (None, f"No unit is stated for this line (RFQ unit: {item.unit}).")
    factor = units.convert(Decimal(1), line.unit, item.unit)
    if not factor:
        return None, f"Quoted per {line.unit_text or line.unit}, which cannot be compared with {item.unit}."
    return factor, None


def _rfq_unit_price(line: QuotedLineItem, item: RequestedItem, a: Assumptions) -> tuple[Decimal | None, str | None]:
    """The line's price per RFQ unit (after the price basis and unit conversion), or why it cannot be had."""
    price = line.price_per_unit
    if price is None or price == 0:
        return None, "unpriced"
    factor, why = unit_factor(line, item, a)
    return (price / factor, None) if factor else (None, why)


def build_offers(rfq: RFQ, quotes: list[Quotation], a: Assumptions, rates: dict[str, Decimal]) -> tuple[list[Offer], list[Exclusion], int]:
    base = config.COMPARISON_CURRENCY
    items = {i.item_id: i for i in rfq.items}
    offers: list[Offer] = []
    exclusions: list[Exclusion] = []
    count = 0
    for quote in quotes:
        name, qid = quote.display_name, quote.quotation_id
        for line in quote.lines:
            count += 1

            def out(code: str, message: str) -> None:
                exclusions.append(Exclusion(qid, name, line.line_id, line.matched_rfq_item_id, code, message))

            item = items.get(line.matched_rfq_item_id or "")
            label = line.source_description
            if line.excluded:
                out("excluded", f"“{label}” was excluded by you.")
            elif item is None or line.match_status not in ("matched", "possible"):
                out("unmatched", f"“{label}” is not one of your RFQ items.")
            elif line.price_per_unit is None or line.price_per_unit == 0:
                out("unpriced", f"“{label}” has no price.")
            elif _open(line) and not a.include_flagged:
                out("flagged", f"“{label}” still has an open review point.")
            else:
                price, why = _rfq_unit_price(line, item, a)
                if price is None:
                    out("unit", why or f"“{label}” cannot be compared.")
                    continue
                notes: list[str] = []
                basis = line_tax_basis(line, quote)
                if basis == "inclusive":
                    rate = tax_rate(line, quote)
                    if rate is None:
                        out("tax", f"“{label}” includes tax but the rate is not stated, so tax cannot be taken out.")
                        continue
                    price = price / (1 + rate / 100)
                    notes.append(f"tax {rate:g}% taken out")
                elif basis == "unclear":
                    notes.append("tax basis not confirmed; compared as quoted")
                currency = line.currency or quote.currency
                if not currency:
                    out("currency", f"“{label}” has no stated currency.")
                    continue
                cost = price * (item.quantity or Decimal(0))
                rate_to_base = Decimal(1) if currency == base else rates.get(currency)
                if _open(line):
                    notes.append("has an open review point")
                factor = unit_factor(line, item, a)[0] or Decimal(1)
                offers.append(Offer(qid, name, item.item_id, line.line_id, price, currency, cost,
                                    cost * rate_to_base if rate_to_base else None, _open(line), tuple(notes),
                                    line.quantity * factor if line.quantity else None,
                                    line.moq * factor if line.moq else None, line.unit_price_text or ""))
    # one offer per vendor and item: the lowest where a vendor gives options
    best: dict[tuple[str, str], Offer] = {}
    for offer in sorted(offers, key=lambda o: (o.cost_base is None, o.cost_base or o.cost)):
        key = (offer.vendor_id, offer.item_id)
        if key in best:
            exclusions.append(Exclusion(offer.vendor_id, offer.vendor, offer.line_id, offer.item_id, "option",
                                        f"Another offer from {offer.vendor} for the same item is lower, so this option is not counted."))
        else:
            best[key] = offer
    return list(best.values()), exclusions, count


def ranked(offers: list[Offer]) -> list[Offer]:
    """Offers that can be ranked: those with a cost in the comparison currency."""
    return [o for o in offers if o.cost_base is not None]


def lowest_by_item(offers: list[Offer], item_ids: list[str]) -> dict[str, list[Offer]]:
    out: dict[str, list[Offer]] = {}
    for item_id in item_ids:
        here = [o for o in ranked(offers) if o.item_id == item_id]
        if not here:
            continue
        low = min(money(o.cost_base) for o in here)  # type: ignore[arg-type]
        out[item_id] = sorted((o for o in here if money(o.cost_base) == low), key=lambda o: o.vendor)  # type: ignore[arg-type]
    return out


def single_vendor(offers: list[Offer], rfq: RFQ, vendors: dict[str, str]) -> list[Scenario]:
    out = []
    for vid, name in vendors.items():
        mine = {o.item_id: o for o in ranked(offers) if o.vendor_id == vid}
        missing = [i.item_id for i in rfq.items if i.item_id not in mine]
        total = sum((o.cost_base for o in mine.values()), Decimal(0)) if mine else None  # type: ignore[misc]
        out.append(Scenario("single_vendor", name, not missing, money(total) if total is not None else None, len(mine),
                            mine, missing, [vid]))
    return sorted(out, key=lambda s: (not s.complete, s.total if s.total is not None else Decimal("Infinity")))


def hybrid(offers: list[Offer], rfq: RFQ, vendors: dict[str, str], max_vendors: int | None = None) -> Scenario:
    """The lowest offer for each item. With a vendor limit, the group of vendors covering the most items at the lowest cost."""
    pool = ranked(offers)
    vids = [v for v in vendors if any(o.vendor_id == v for o in pool)]
    limit = max_vendors if max_vendors and max_vendors > 0 else len(vids)
    best: tuple[int, Decimal, dict[str, Offer]] | None = None
    for size in range(1, min(limit, len(vids)) + 1):
        for group in itertools.combinations(vids, size):
            pick: dict[str, Offer] = {}
            for o in pool:
                if o.vendor_id in group and (o.item_id not in pick or o.cost_base < pick[o.item_id].cost_base):  # type: ignore[operator]
                    pick[o.item_id] = o
            total = sum((o.cost_base for o in pick.values()), Decimal(0))  # type: ignore[misc]
            if best is None or (len(pick), -total) > (best[0], -best[1]):
                best = (len(pick), total, pick)
    pick = best[2] if best else {}
    missing = [i.item_id for i in rfq.items if i.item_id not in pick]
    total = sum((o.cost_base for o in pick.values()), Decimal(0)) if pick else None  # type: ignore[misc]
    used = sorted({o.vendor_id for o in pick.values()}, key=lambda v: vendors[v])
    label = "Indicative lowest-cost combination" + (f" (at most {max_vendors} vendors)" if max_vendors else "")
    return Scenario("hybrid", label, not missing and bool(pick), money(total) if total is not None else None, len(pick),
                    pick, missing, used)


def analyse(rfq: RFQ, quotes: list[Quotation], assumptions: Assumptions | None = None,
            rates: dict[str, Decimal] | None = None) -> Analysis:
    """Run the whole comparison for the quotations the buyer kept."""
    a = assumptions or Assumptions()
    rates = {**(rates or {}), **a.fx_rate_override}
    live = [q for q in quotes if q.status not in ("rejected", "failed") and not q.excluded and q.quotation_id not in a.exclude_vendor_ids]
    vendors = {q.quotation_id: q.display_name for q in live}
    offers, exclusions, count = build_offers(rfq, live, a, rates)
    base = config.COMPARISON_CURRENCY
    missing_rates = {o.currency for o in offers if o.cost_base is None}
    notes = []
    for currency in sorted(missing_rates):
        n = sum(1 for o in offers if o.currency == currency and o.cost_base is None)
        notes.append(f"{n} offer{'s' if n != 1 else ''} in {currency} {'are' if n != 1 else 'is'} left out of the ranking: no exchange rate to {base}.")
    return Analysis(
        rfq_id=rfq.rfq_id, base_currency=base, assumptions=a, offers=offers, exclusions=exclusions, vendors=vendors,
        lowest=lowest_by_item(offers, [i.item_id for i in rfq.items]), singles=single_vendor(offers, rfq, vendors),
        hybrid=hybrid(offers, rfq, vendors, a.max_vendors), unconverted_currencies=missing_rates, notes=notes, line_count=count)
