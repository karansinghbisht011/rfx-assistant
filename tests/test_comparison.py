from decimal import Decimal as D

from app.schemas.analysis import Assumptions
from app.schemas.flags import ReviewFlag
from app.schemas.quotation import Charge, Quotation, QuotedLineItem
from app.schemas.rfq import RFQ, RequestedItem
from app.services import comparison as cmp


def rfq():
    return RFQ(name="r", items=[
        RequestedItem(item_id="a", original_text="2 pumps", catalogue_title="Pumps", quantity=D(2), unit="Nos"),
        RequestedItem(item_id="b", original_text="40 kg rods", catalogue_title="Rods", quantity=D(40), unit="Kg"),
        RequestedItem(item_id="c", original_text="10 sets ties", catalogue_title="Ties", quantity=D(10), unit="Set"),
    ])


def line(item, price, unit="Nos", cur="INR", **kw):
    return QuotedLineItem(source_description=f"line {item}", matched_rfq_item_id=item, match_status="matched", unit_price=D(price),
                          unit=unit, unit_text=unit, currency=cur, quantity=D(1), **kw)


def quote(name, *lines, **kw):
    base = dict(source_filename=f"{name}.xlsx", vendor_name=name, status="validated", currency="INR", tax_basis="exclusive", lines=list(lines))
    return Quotation(**{**base, **kw})


def run(quotes, **kw):
    return cmp.analyse(rfq(), quotes, **kw)


def test_lowest_per_item_single_vendor_and_hybrid():
    q1 = quote("V1", line("a", 100), line("b", 10, "Kg"), line("c", 5, "Set"))
    q2 = quote("V2", line("a", 90), line("b", 12, "Kg"), line("c", 6, "Set"))
    r = run([q1, q2])
    assert r.lowest["a"][0].vendor == "V2" and r.lowest["b"][0].vendor == "V1"
    assert [s.label for s in r.singles if s.complete] == ["V1", "V2"]            # cheapest first
    assert r.singles[0].total == D("650.00") and r.singles[1].total == D("720.00")  # 200+400+50, 180+480+60
    assert r.hybrid.total == D("630.00") and r.hybrid.complete                      # 180 + 400 + 50
    assert r.reconciles()


def test_price_basis_and_unit_conversion_are_applied_exactly():
    per_hundred = line("a", 4000, price_basis_quantity=D(100))        # 40 per piece
    tonne = line("b", 9000, "Tonne")                                   # 9 per kg
    r = run([quote("V", per_hundred, tonne)])
    prices = {o.item_id: o.unit_price for o in r.offers}
    assert prices["a"] == D(40) and prices["b"] == D(9)


def test_count_units_that_cannot_convert_are_left_out_with_a_reason():
    r = run([quote("V", line("c", 99, "Pack"))])
    assert not r.offers and r.exclusions[0].code == "unit" and "cannot be compared" in r.exclusions[0].message


def test_missing_unit_needs_the_assumption():
    l = line("a", 10)
    l.unit = l.unit_text = None
    assert run([quote("V", l)]).exclusions[0].code == "unit"
    assert run([quote("V", l)], assumptions=Assumptions(use_rfq_unit_for_missing=True)).offers


def test_tax_inclusive_prices_have_tax_taken_out_only_when_the_rate_is_stated():
    with_rate = line("a", 118, tax_text="inclusive of GST at 18%")
    no_rate = line("b", 118, "Kg", tax_text="inclusive of GST")
    r = run([quote("V", with_rate, no_rate)])
    assert r.offers[0].unit_price == D(100) and "tax 18% taken out" in r.offers[0].notes[0]
    assert r.exclusions[0].code == "tax"


def test_a_quote_wide_tax_rate_is_used_when_there_is_exactly_one():
    q = quote("V", line("a", 118), tax_basis="inclusive", charges=[Charge(kind="tax", scope="quote", text="GST @ 18%")])
    assert run([q]).offers[0].unit_price == D(100)


def test_flagged_lines_wait_until_the_buyer_includes_them():
    flagged = line("a", 21500)
    flagged.flags = [ReviewFlag(code="Q22", severity="review", scope="quote_line", scope_id=flagged.line_id, message="x")]
    q = quote("V", flagged)
    assert run([q]).exclusions[0].code == "flagged"
    on = run([q], assumptions=Assumptions(include_flagged=True))
    assert on.offers and on.offers[0].flagged


def test_foreign_currency_needs_a_rate_and_never_a_guess():
    q = quote("V", line("a", 10, cur="USD"))
    r = run([q])
    assert r.lowest == {} and "USD" in r.unconverted_currencies and "no exchange rate" in r.notes[0]
    r = run([q], rates={"USD": D("90")})
    assert r.lowest["a"][0].cost_base == D(1800) and not r.notes
    r = run([q], assumptions=Assumptions(fx_rate_override={"USD": D("100")}), rates={"USD": D("90")})
    assert r.lowest["a"][0].cost_base == D(2000)          # the buyer's rate wins


def test_options_count_once_at_the_lowest_price():
    r = run([quote("V", line("a", 100), line("a", 80))])
    assert len(r.offers) == 1 and r.offers[0].unit_price == D(80)
    assert [e.code for e in r.exclusions] == ["option"] and r.reconciles()


def test_ties_are_listed_and_incomplete_vendors_are_not_single_vendor_winners():
    r = run([quote("A", line("a", 50)), quote("B", line("a", 50), line("b", 5, "Kg"), line("c", 1, "Set"))])
    assert [o.vendor for o in r.lowest["a"]] == ["A", "B"]
    assert [s.complete for s in r.singles] == [True, False] and r.singles[0].label == "B"


def test_hybrid_is_incomplete_when_an_item_has_no_offer():
    r = run([quote("A", line("a", 50))])
    assert not r.hybrid.complete and r.hybrid.missing_item_ids == ["b", "c"]


def test_vendor_limit_picks_the_best_group():
    a = quote("A", line("a", 10), line("b", 10, "Kg"), line("c", 10, "Set"))      # 20 + 400 + 100 = 520
    b = quote("B", line("a", 1), line("b", 20, "Kg"), line("c", 20, "Set"))       # 2 + 800 + 200
    c = quote("C", line("a", 50), line("b", 1, "Kg"), line("c", 1, "Set"))        # 100 + 40 + 10
    free = run([a, b, c]).hybrid
    assert free.total == D("52.00") and len(free.vendor_ids) == 2                   # B for pumps, C for the rest
    one = run([a, b, c], assumptions=Assumptions(max_vendors=1)).hybrid
    assert one.complete and len(one.vendor_ids) == 1 and one.total == D("150.00")  # C alone: 100+40+10


def test_excluded_vendors_and_lines_stay_out():
    q1, q2 = quote("A", line("a", 10)), quote("B", line("a", 20))
    assert run([q1, q2], assumptions=Assumptions(exclude_vendor_ids=[q1.quotation_id])).lowest["a"][0].vendor == "B"
    q1.lines[0].excluded = True
    r = run([q1, q2])
    assert r.lowest["a"][0].vendor == "B" and r.exclusions[0].code == "excluded" and r.reconciles()


# ------------------------------------------------------------------ exchange rates
def test_rates_come_with_their_source_and_bad_lookups_give_nothing(monkeypatch):
    from app.services import fx
    import httpx

    class Reply:
        def __init__(self, data): self.data = data
        def raise_for_status(self): pass
        def json(self): return self.data

    class Http:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def get(self, url, params): 
            if params["base"] == "XXX":
                raise httpx.ConnectError("down")
            return Reply({"date": "2026-10-01", "rates": {"INR": 96.33}})

    monkeypatch.setattr(fx.httpx, "Client", Http)
    got = fx.fetch_rates({"USD", "XXX", "INR"})
    assert set(got) == {"USD"} and got["USD"].rate == D("96.33") and "Frankfurter" in got["USD"].source and got["USD"].as_of == "2026-10-01"
    assert fx.manual_rate("USD", D("0")) is None and fx.manual_rate("USD", D("88")).manual
