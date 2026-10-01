from datetime import date
from decimal import Decimal as D

import pytest

from app.services.quote_parsing import (
    AMBIGUOUS_DOLLAR, detect_currency, detect_tax_basis, number_in_source, parse_amount, parse_basis,
    parse_date_text, parse_quote_quantity, parse_validity,
)


@pytest.mark.parametrize("text,value", [
    ("Rs 47,000 each", D("47000")), ("₹12,500.00", D("12500.00")), ("12,50,000.00", D("1250000.00")),
    ("1.25 lakh", D("125000.00")), ("USD 520.00", D("520.00")), ("6.5", D("6.5")),
    ("on request", None), ("same rate as our last supply", None), ("", None), (None, None),
])
def test_parse_amount(text, value):
    assert parse_amount(text) == value


@pytest.mark.parametrize("text,code", [
    ("Rs 47,000", "INR"), ("₹ 100", "INR"), ("INR", "INR"), ("USD 520", "USD"), ("US$ 5", "USD"), ("EUR 10", "EUR"),
    ("$100", AMBIGUOUS_DOLLAR), ("12,500", None), (None, None),
])
def test_detect_currency(text, code):
    assert detect_currency(text) == code


@pytest.mark.parametrize("text,qty,ok", [
    ("1,250.00 per 100 nos", D(100), True), ("per kg", D(1), True), ("each", D(1), True), ("per 1000", D(1000), True),
])
def test_parse_basis_recognised(text, qty, ok):
    b = parse_basis(text)
    assert b.quantity == qty and b.recognised is ok


def test_parse_basis_absent_and_unrecognised():
    assert parse_basis(None).quantity is None and parse_basis(None).recognised
    assert not parse_basis("weird basis").recognised


@pytest.mark.parametrize("texts,basis", [
    (["inclusive of GST at 18%"], "inclusive"), (["GST 18% extra"], "exclusive"), (["exclusive of GST"], "exclusive"),
    (["GST @ 18%"], "unclear"), (["freight extra"], "unclear"), (["inclusive of GST", "GST extra"], "unclear"),
])
def test_detect_tax_basis(texts, basis):
    assert detect_tax_basis(*texts) == basis


def test_dates_and_validity():
    assert parse_date_text("Mon, 5 Oct 2026 at 4:12 PM") == date(2026, 10, 5)
    assert parse_date_text("03 October 2026") == date(2026, 10, 3)
    assert parse_date_text("2026-10-03") == date(2026, 10, 3)
    assert parse_date_text("03/10/2026") == date(2026, 10, 3)
    assert parse_date_text("soon") is None
    assert parse_validity("15 days from date of quotation", date(2026, 10, 2)) == date(2026, 10, 17)
    assert parse_validity("valid till 20 Oct 2026", None) == date(2026, 10, 20)
    assert parse_validity("Subject to prior sale", date(2026, 10, 2)) is None
    assert parse_validity("15 days", None) is None  # a period needs a start date


def test_quantity_and_grounding():
    assert parse_quote_quantity("150 mtr") == 150 and parse_quote_quantity("a dozen") == 12
    assert parse_quote_quantity("10-12") is None and parse_quote_quantity(None) is None
    assert number_in_source(D("47800"), "1 | Pumps | 2 | Nos | 47,800.00")
    assert number_in_source(D("21500"), "6. Ball valve - 10 nos @ Rs 21,500 each")
    assert not number_in_source(D("2150"), "6. Ball valve - 10 nos @ Rs 21,500 each")
    assert not number_in_source(None, "anything")
