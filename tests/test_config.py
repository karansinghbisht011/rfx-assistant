import csv

from app import config


def test_catalogue_units_are_canonical():
    with open(config.CATALOGUE_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 13326
    assert len({r["commodity_code"] for r in rows}) == len(rows)
    assert {r["default_unit"] for r in rows} <= set(config.CANONICAL_UNITS)


def test_count_units_are_canonical():
    assert set(config.COUNT_UNITS) <= set(config.CANONICAL_UNITS)


def test_thresholds_are_ordered():
    assert config.MATCH_LOW < config.MATCH_HIGH <= 100
