"""Cheapest purchase from several vendors under the buyer's rules. Pure code, no AI, no network.

Quantities are whole RFQ units when an item may be split, and the whole required quantity from one vendor otherwise.
Unit prices are flat (no volume tiers). The problem is a small mixed-integer program solved exactly; every figure
is recomputed afterwards in Decimal from the integer quantities.
"""

import math
from dataclasses import dataclass, field
from decimal import Decimal

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from app import config
from app.schemas.rfq import RequestedItem
from app.services.comparison import Offer

TIE_BREAK = 1e-7     # keeps equal-cost answers stable (vendor name order) without changing any real optimum
RULE_ORDER = ("pins", "max_vendors", "min_items", "required")   # the order in which rules are relaxed to find the culprit


@dataclass
class Rules:
    allow_split: bool = False
    min_items_per_vendor: int = 0
    required: set[str] = field(default_factory=set)             # vendors that must supply something
    max_vendors: int | None = None
    pins: list[tuple[str, str, Decimal | None]] = field(default_factory=list)   # (item_id, vendor_id, quantity or whole)


@dataclass
class Share:
    item_id: str
    vendor_id: str
    quantity: Decimal
    offer: Offer
    demand: Decimal = Decimal(0)        # the item's required quantity, which the offer's cost is for

    @property
    def total(self) -> Decimal:
        return self.offer.cost_base / self.demand * self.quantity if self.demand else Decimal(0)  # type: ignore[operator]


@dataclass
class Allocation:
    shares: list[Share]
    unfilled: dict[str, Decimal]            # item_id -> quantity nobody could supply
    feasible: bool
    unmet: list[tuple[str, str]] = field(default_factory=list)   # (rule name, reason) for rules that could not be kept

    @property
    def total(self) -> Decimal:
        return sum((s.total for s in self.shares), Decimal(0))


def _unit_cost(offer: Offer, demand: Decimal) -> Decimal:
    return offer.cost_base / demand  # type: ignore[operator]


def _splittable(item: RequestedItem, rules: Rules) -> bool:
    qty = item.quantity or Decimal(0)
    pinned_part = any(i == item.item_id and q is not None for i, _, q in rules.pins)
    return qty >= 1 and qty == qty.to_integral_value() and (rules.allow_split or pinned_part)


def _solve_once(items: list[RequestedItem], offers: list[Offer], rules: Rules) -> Allocation | None:
    """One exact solve. None when the rules cannot all be met."""
    by_item = {i.item_id: i for i in items if i.quantity and i.quantity > 0}
    pool: list[tuple[Offer, Decimal, Decimal, Decimal, bool]] = []     # offer, demand, cap, lower bound, splittable
    for o in sorted((o for o in offers if o.cost_base is not None and o.item_id in by_item), key=lambda o: (o.vendor, o.item_id)):
        item = by_item[o.item_id]
        demand = item.quantity  # type: ignore[assignment]
        split = _splittable(item, rules)
        cap = min(demand, o.quoted_qty) if o.quoted_qty else demand
        if split:
            cap = Decimal(math.floor(cap))
            if cap < 1:
                continue
            lower = min(Decimal(max(1, math.ceil(o.moq))) if o.moq else Decimal(1), cap)
        else:
            if cap < demand:                 # a whole-item purchase needs the vendor to cover all of it
                continue
            lower = demand
        pool.append((o, demand, cap, lower, split))
    vendors = sorted({o.vendor_id for o, *_ in pool}, key=lambda v: next(o.vendor for o, *_ in pool if o.vendor_id == v))
    item_ids = list(by_item)
    K, V, I = len(pool), len(vendors), len(item_ids)
    if K == 0:
        return Allocation([], {i: by_item[i].quantity for i in item_ids}, True)  # type: ignore[misc]
    vrank = {v: n for n, v in enumerate(vendors)}
    n = 2 * K + V + I
    q_ix, w_ix = (lambda k: k), (lambda k: K + k)
    y_ix, u_ix = (lambda v: 2 * K + vrank[v]), (lambda i: 2 * K + V + item_ids.index(i))

    lo, hi = np.zeros(n), np.ones(n)
    integrality = np.zeros(n)
    for k, (o, demand, cap, lower, split) in enumerate(pool):
        hi[q_ix(k)] = float(cap)
        integrality[q_ix(k)] = 1 if split else 0
        integrality[w_ix(k)] = 1
    for v in vendors:
        integrality[y_ix(v)] = 1
    for i in item_ids:
        hi[u_ix(i)] = float(by_item[i].quantity)  # type: ignore[arg-type]

    rows, lows, highs = [], [], []

    def add(coeffs: dict[int, float], low: float, high: float) -> None:
        row = np.zeros(n)
        for j, c in coeffs.items():
            row[j] += c
        rows.append(row), lows.append(low), highs.append(high)

    for i in item_ids:
        coeffs = {q_ix(k): 1.0 for k, p in enumerate(pool) if p[0].item_id == i}
        coeffs[u_ix(i)] = 1.0
        add(coeffs, float(by_item[i].quantity), float(by_item[i].quantity))  # type: ignore[arg-type]
        if not _splittable(by_item[i], rules):
            add({w_ix(k): 1.0 for k, p in enumerate(pool) if p[0].item_id == i}, 0, 1)
    for k, (o, demand, cap, lower, split) in enumerate(pool):
        if split:
            add({q_ix(k): 1.0, w_ix(k): -float(cap)}, -np.inf, 0)
            add({q_ix(k): 1.0, w_ix(k): -float(lower)}, 0, np.inf)
        else:
            add({q_ix(k): 1.0, w_ix(k): -float(demand)}, 0, 0)
        add({w_ix(k): 1.0, y_ix(o.vendor_id): -1.0}, -np.inf, 0)
    min_items = max(0, rules.min_items_per_vendor)
    for v in vendors:
        mine = [k for k, p in enumerate(pool) if p[0].vendor_id == v]
        add({**{w_ix(k): 1.0 for k in mine}, y_ix(v): -float(max(1, min_items))}, 0, np.inf)   # used => at least that many lines
        add({**{w_ix(k): -1.0 for k in mine}, y_ix(v): 1.0}, -np.inf, 0)                         # used => supplies something
    if rules.max_vendors:
        add({y_ix(v): 1.0 for v in vendors}, 0, float(rules.max_vendors))
    for v in rules.required:
        if v not in vrank:
            return None
        lo[y_ix(v)] = 1
    for item_id, vendor_id, qty in rules.pins:
        ks = [k for k, p in enumerate(pool) if p[0].item_id == item_id and p[0].vendor_id == vendor_id]
        if not ks:
            return None
        want = by_item[item_id].quantity if qty is None or not _splittable(by_item[item_id], rules) else qty
        if want > hi[q_ix(ks[0])] + 1e-9:
            return None
        lo[q_ix(ks[0])] = hi[q_ix(ks[0])] = float(want)  # type: ignore[arg-type]
        lo[w_ix(ks[0])] = 1

    constraints = LinearConstraint(np.array(rows), np.array(lows), np.array(highs))
    options = {"mip_rel_gap": 0.0, "time_limit": float(config.SOLVER_TIME_LIMIT_SECONDS), "disp": False}
    coverage = np.zeros(n)
    for i in item_ids:
        coverage[u_ix(i)] = 1.0 / float(by_item[i].quantity)  # type: ignore[arg-type]
    first = milp(coverage, constraints=constraints, integrality=integrality, bounds=Bounds(lo, hi), options=options)
    if first.status != 0:
        return None
    least_unfilled = float(coverage @ first.x)
    cost = np.zeros(n)
    for k, (o, demand, *_rest) in enumerate(pool):
        cost[q_ix(k)] = float(_unit_cost(o, demand)) + TIE_BREAK * (vrank[o.vendor_id] + 1)
    bound = LinearConstraint(coverage.reshape(1, -1), -np.inf, least_unfilled + 1e-7)
    second = milp(cost, constraints=[constraints, bound], integrality=integrality, bounds=Bounds(lo, hi), options=options)
    if second.status != 0:
        return None

    shares = []
    filled: dict[str, Decimal] = {i: Decimal(0) for i in item_ids}
    for k, (o, demand, cap, lower, split) in enumerate(pool):
        value = second.x[q_ix(k)]
        if value < 0.5 / max(1.0, float(demand)) and second.x[w_ix(k)] < 0.5:
            continue
        quantity = Decimal(int(round(value))) if split else demand
        if quantity <= 0:
            continue
        shares.append(Share(o.item_id, o.vendor_id, quantity, o, demand))
        filled[o.item_id] += quantity
    unfilled = {i: by_item[i].quantity - filled[i] for i in item_ids if by_item[i].quantity - filled[i] > 0}  # type: ignore[operator]
    return Allocation(shares, unfilled, True)


def solve(items: list[RequestedItem], offers: list[Offer], rules: Rules | None = None) -> Allocation:
    """The cheapest purchase that keeps the rules. A rule that cannot be kept is dropped, and reported in `unmet`."""
    rules = rules or Rules()
    first = _solve_once(items, offers, rules)
    if first is not None:
        return first
    reasons = {
        "pins": "A requested vendor does not have a comparable offer for that item, or not enough quantity.",
        "max_vendors": "The items cannot all be supplied by that few vendors.",
        "min_items": "Not every vendor has enough comparable offers to supply that many items.",
        "required": "A required vendor has no comparable offer.",
    }
    if rules.max_vendors and len(rules.required) > rules.max_vendors:
        reasons["max_vendors"] = (f"Giving {len(rules.required)} vendors a share needs more than {rules.max_vendors} vendors, "
                                  "so the limit was not kept.")
    relaxed = Rules(rules.allow_split, rules.min_items_per_vendor, set(rules.required), rules.max_vendors, list(rules.pins))
    dropped: list[tuple[str, str]] = []
    for name in RULE_ORDER:
        if name == "pins" and relaxed.pins:
            relaxed.pins = []
        elif name == "max_vendors" and relaxed.max_vendors:
            relaxed.max_vendors = None
        elif name == "min_items" and relaxed.min_items_per_vendor:
            relaxed.min_items_per_vendor = 0
        elif name == "required" and relaxed.required:
            relaxed.required = set()
        else:
            continue
        dropped.append((name, reasons[name]))
        result = _solve_once(items, offers, relaxed)
        if result is not None:
            result.unmet = dropped
            return result
    return Allocation([], {i.item_id: i.quantity for i in items if i.quantity}, False, dropped)  # type: ignore[misc]
