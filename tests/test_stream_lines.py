import json

import pytest

from app.services.stream_lines import LineStreamParser

ANSWER = {
    "is_quotation": True, "vendor": 'Acme "Quality" {Works}', "quote_ref": "Q-1",
    "lines": [
        {"ref": "R1", "desc": 'Pump, 2" {flanged} \\ type', "qty": "2", "price": "Rs 47,000"},
        {"ref": "R2", "desc": "Cable ]tricky[", "note": 'says "same as last"'},
        {"ref": "R3", "desc": "Valve", "src": "3. Valve - 10 nos @ 2,240"},
    ],
    "charges": [{"kind": "tax", "scope": "quote", "text": "GST 18% extra"}],
}


def collect(text: str, size: int) -> list[dict]:
    parser, out = LineStreamParser(), []
    for i in range(0, len(text), size):
        out += parser.feed(text[i:i + size])
    return out


@pytest.mark.parametrize("size", [1, 2, 3, 5, 7, 11, 16, 50, 10_000])
def test_finds_every_line_whatever_the_chunk_size(size):
    text = json.dumps(ANSWER)
    assert collect(text, size) == ANSWER["lines"]


def test_lines_arrive_as_soon_as_they_close_not_at_the_end():
    text = json.dumps(ANSWER)
    parser = LineStreamParser()
    cut = text.index('"R2"')  # the middle of the second line
    first = parser.feed(text[:cut])
    assert [l["ref"] for l in first] == ["R1"]
    assert [l["ref"] for l in parser.feed(text[cut:])] == ["R2", "R3"]


def test_braces_quotes_and_brackets_inside_strings_do_not_confuse_it():
    got = collect(json.dumps(ANSWER, indent=2), 4)
    assert got[0]["desc"] == 'Pump, 2" {flanged} \\ type' and got[1]["desc"] == "Cable ]tricky["


def test_nothing_is_emitted_before_the_lines_array_or_for_a_broken_object():
    assert collect('{"is_quotation": true, "vendor": "x"', 3) == []
    parser = LineStreamParser()
    assert parser.feed('{"lines": [{"ref": "R1", "desc": ') == []  # a partial object waits
    assert parser.feed('"ok"}, {"ref": nope}]}') == [{"ref": "R1", "desc": "ok"}]  # a broken one is skipped, not fatal


def test_charges_after_the_lines_are_not_mistaken_for_lines():
    assert [l["ref"] for l in collect(json.dumps(ANSWER), 6)] == ["R1", "R2", "R3"]
