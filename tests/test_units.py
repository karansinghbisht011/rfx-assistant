from decimal import Decimal

import pytest

from app.services import units
from app.services.quantities import check_quantity, format_quantity, parse_quantity


@pytest.mark.parametrize(
    "text,expected",
    [("nos", "Nos"), ("PCS", "Nos"), ("Mtrs", "Metre"), ("m", "Metre"), ("ltr", "Litre"), ("MT", "Tonne"),
     ("kgs", "Kg"), ("pairs", "Pair"), ("Boxes", "Box"), (" no. ", "Nos")],
)
def test_normalize_unit(text, expected):
    assert units.normalize_unit(text) == expected


def test_unknown_unit_is_not_guessed():
    assert units.normalize_unit("bundles") is None
    assert units.normalize_unit(None) is None
    assert units.normalize_unit("g") is None  # quote-side only
    assert units.normalize_unit("g", quote_side=True) == "g"


def test_conversions_within_dimension():
    assert units.convert(Decimal("2"), "Tonne", "Kg") == Decimal("2000")
    assert units.convert(Decimal("250"), "cm", "Metre") == Decimal("2.5")
    assert units.convert(Decimal("1500"), "ml", "Litre") == Decimal("1.5")
    assert units.convert(Decimal("3"), "Kg", "Kg") == Decimal("3")


def test_no_conversion_across_dimensions_or_between_count_units():
    assert units.convert(Decimal("1"), "Kg", "Litre") is None
    assert units.convert(Decimal("1"), "Box", "Nos") is None
    assert units.convert(Decimal("1"), "Box", "Pack") is None


def test_discrete_units():
    assert units.is_discrete("Nos") and not units.is_discrete("Kg") and not units.is_discrete(None)


@pytest.mark.parametrize(
    "text,value,problem",
    [("4", Decimal("4"), None), ("1,000", Decimal("1000"), None), ("2.5", Decimal("2.5"), None),
     ("ten", Decimal("10"), None), ("a dozen", Decimal("12"), None), ("two dozen", Decimal("24"), None),
     ("10-12", None, "range"), ("10 to 12", None, "range"), ("many", None, "unparsable"),
     ("0", None, "nonpositive"), ("-3", None, "unparsable"), ("99999999", None, "too_large"), ("", None, None)],
)
def test_parse_quantity(text, value, problem):
    result = parse_quantity(text)
    assert result.value == value and result.problem == problem


def test_check_quantity_and_format():
    assert check_quantity(Decimal("-1")).problem == "nonpositive"
    assert format_quantity(Decimal("4.0")) == "4"
    assert format_quantity(Decimal("2.50")) == "2.5"
    assert format_quantity(Decimal("1000")) == "1000"
    assert format_quantity(None) == ""
