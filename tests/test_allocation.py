import itertools
import random
from decimal import Decimal as D

import pytest

from app.schemas.rfq import RequestedItem
from app.services.allocation import Rules, solve
from app.services.comparison import Offer


def item(i, qty, unit="Nos"):
    return RequestedItem(item_id=i, original_text=i, catalogue_title=i, quantity=D(str(qty)), unit=unit)


def offer(vendor, i, unit_price, qty, quoted=None, moq=None):
    return Offer(vendor, vendor, i, f"{vendor}-{i}", D(str(unit_price)), "INR", D(str(unit_price)) * D(str(qty)),
                 D(str(unit_price)) * D(str(qty)), quoted_qty=D(str(quoted)) if quoted is not None else None,
                 moq=D(str(moq)) if moq is not None else None)


ITEMS = [item("a", 4), item("b", 3), item("c", 2)]
OFFERS = [offer("A", "a", 10, 4), offer("A", "b", 30, 3), offer("A", "c", 50, 2),
          offer("B", "a", 12, 4), offer("B", "b", 20, 3), offer("B", "c", 55, 2),
          offer("C", "a", 9, 4), offer("C", "b", 35, 3), offer("C", "c", 40, 2)]


def by(alloc):
    out = {}
    for s in alloc.shares:
        out.setdefault(s.item_id, {})[s.vendor_id] = s.quantity
    return out


def test_no_rules_gives_the_lowest_offer_for_each_item():
    r = solve(ITEMS, OFFERS)
    assert by(r) == {"a": {"C": 4}, "b": {"B": 3}, "c": {"C": 2}} and r.total == D(36 + 60 + 80) and not r.unmet and not r.unfilled


def test_every_vendor_supplies_without_splitting_assigns_whole_items():
    r = solve(ITEMS, OFFERS, Rules(required={"A", "B", "C"}))
    assert {s.vendor_id for s in r.shares} == {"A", "B", "C"} and all(len(v) == 1 for v in by(r).values())
    assert r.total == D(40 + 60 + 80)        # A-a 40, B-b 60, C-c 80 is the cheapest one-item-each assignment


def test_splitting_lets_a_vendor_in_for_a_single_unit_at_lower_cost():
    whole = solve(ITEMS, OFFERS, Rules(required={"A", "B", "C"}))
    split = solve(ITEMS, OFFERS, Rules(allow_split=True, required={"A", "B", "C"}))
    assert split.total <= whole.total and {s.vendor_id for s in split.shares} == {"A", "B", "C"}
    for i in ITEMS:   # quantities add up exactly to what the RFQ asks for
        assert sum(s.quantity for s in split.shares if s.item_id == i.item_id) == i.quantity
    assert split.total >= D(176)            # never cheaper than the unconstrained purchase


def test_min_items_and_max_vendors():
    r = solve(ITEMS, OFFERS, Rules(max_vendors=1))
    assert {s.vendor_id for s in r.shares} == {"C"} or r.total == min(
        sum(o.cost_base for o in OFFERS if o.vendor_id == v) for v in "ABC")
    two = solve(ITEMS, OFFERS, Rules(min_items_per_vendor=2, allow_split=True))
    for v in {s.vendor_id for s in two.shares}:
        assert len({s.item_id for s in two.shares if s.vendor_id == v}) >= 2


def test_pins_whole_and_partial():
    r = solve(ITEMS, OFFERS, Rules(pins=[("a", "A", None)]))
    assert by(r)["a"] == {"A": 4}
    p = solve(ITEMS, OFFERS, Rules(pins=[("a", "A", D(1))]))
    assert by(p)["a"]["A"] == 1 and sum(by(p)["a"].values()) == 4        # a partial pin implies a split


def test_a_vendor_cannot_supply_more_than_it_quoted_for():
    offers = [offer("A", "a", 1, 4, quoted=2), offer("B", "a", 5, 4)]
    r = solve([item("a", 4)], offers, Rules(allow_split=True))
    assert by(r)["a"] == {"A": 2, "B": 2}
    whole = solve([item("a", 4)], offers, Rules())
    assert by(whole)["a"] == {"B": 4}                                       # A cannot cover the whole item


def test_minimum_orders_are_respected():
    offers = [offer("A", "a", 1, 6, moq=4), offer("B", "a", 5, 6)]
    r = solve([item("a", 6)], offers, Rules(allow_split=True, required={"A", "B"}))
    assert by(r)["a"]["A"] >= 4 and sum(by(r)["a"].values()) == 6


def test_unfilled_demand_is_reported_not_invented():
    r = solve(ITEMS + [item("z", 5)], OFFERS)
    assert r.unfilled == {"z": D(5)} and "z" not in by(r)


def test_an_impossible_rule_is_reported_and_the_rest_is_still_solved():
    r = solve(ITEMS, OFFERS, Rules(required={"A", "B", "C", "ghost"}))
    assert [n for n, _ in r.unmet] == ["required"] and r.shares and r.feasible
    r = solve(ITEMS, OFFERS, Rules(max_vendors=1, required={"A", "B"}))
    assert [n for n, _ in r.unmet] == ["max_vendors"] and {s.vendor_id for s in r.shares} >= {"A", "B"}


def test_fractional_quantities_are_bought_whole_from_one_vendor():
    r = solve([item("t", "2.5", "Tonne")], [offer("A", "t", 10, "2.5"), offer("B", "t", 12, "2.5")], Rules(allow_split=True))
    assert by(r) == {"t": {"A": D("2.5")}}


def test_equal_costs_give_the_same_answer_every_time():
    offers = [offer("A", "a", 10, 4), offer("B", "a", 10, 4)]
    runs = {tuple((s.vendor_id, s.quantity) for s in solve([item("a", 4)], offers).shares) for _ in range(5)}
    assert runs == {(("A", D(4)),)}


def brute(items, offers, rules):
    """Every whole-unit purchase, checked against the same rules."""
    best = None
    per_item = []
    for it in items:
        mine = [o for o in offers if o.item_id == it.item_id]
        opts = []
        for combo in itertools.product(*[range(int(min(it.quantity, o.quoted_qty or it.quantity)) + 1) for o in mine]):
            if sum(combo) != it.quantity:
                continue
            if not rules.allow_split and sum(1 for c in combo if c) != 1:
                continue
            opts.append(list(zip(mine, combo)))
        per_item.append(opts)
    for pick in itertools.product(*per_item):
        used: dict[str, set] = {}
        total = D(0)
        for it, opts in zip(items, pick):
            for o, c in opts:
                if c:
                    used.setdefault(o.vendor_id, set()).add(o.item_id)
                    total += o.cost_base / it.quantity * c
        if rules.required and not rules.required <= set(used):
            continue
        if rules.max_vendors and len(used) > rules.max_vendors:
            continue
        if rules.min_items_per_vendor and any(len(v) < rules.min_items_per_vendor for v in used.values()):
            continue
        best = total if best is None or total < best else best
    return best


@pytest.mark.parametrize("seed", range(40))
def test_the_solver_matches_exhaustive_search_on_small_random_cases(seed):
    rng = random.Random(seed)
    items = [item(f"i{n}", rng.randint(1, 3)) for n in range(rng.randint(2, 3))]
    vendors = ["A", "B", "C"][: rng.randint(2, 3)]
    offers = [offer(v, it.item_id, rng.randint(5, 60), it.quantity, quoted=rng.choice([None, rng.randint(1, 3)]))
              for it in items for v in vendors if rng.random() < 0.85]
    rules = Rules(allow_split=rng.random() < 0.6, min_items_per_vendor=rng.choice([0, 0, 2]),
                  required=set(rng.sample(vendors, rng.randint(0, 2))), max_vendors=rng.choice([None, None, 2]))
    expected = brute(items, offers, rules)
    result = solve(items, offers, rules)
    if expected is None or result.unmet or result.unfilled:
        return        # relaxed or partial results are covered by the dedicated tests above
    assert result.total == expected, (seed, rules)


def test_a_vendor_limit_smaller_than_the_required_vendors_is_explained():
    r = solve(ITEMS, OFFERS, Rules(max_vendors=2, required={"A", "B", "C"}))
    assert [n for n, _ in r.unmet] == ["max_vendors"] and "3 vendors" in r.unmet[0][1] and {s.vendor_id for s in r.shares} == {"A", "B", "C"}
