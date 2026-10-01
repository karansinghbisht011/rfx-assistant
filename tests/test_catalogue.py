import pandas as pd
import pytest

from app.services.catalogue_service import Catalogue, CatalogueError, normalize


@pytest.fixture(scope="module")
def catalogue():
    return Catalogue.load()


def test_loads_full_catalogue(catalogue):
    assert len(catalogue) == 13326


def test_exact_match_ignores_case_and_plurals(catalogue):
    assert catalogue.exact("pressure transmitter").title == "Pressure transmitters"
    assert catalogue.exact("PRESSURE TRANSMITTERS!").code == catalogue.exact("pressure transmitter").code


def test_clear_winner_is_resolved_by_code(catalogue):
    terms = ["pressure transmitters"]
    status, winner = catalogue.decide(terms, catalogue.shortlist(terms))
    assert status == "exact" and winner.title == "Pressure transmitters"


def test_generic_term_is_ambiguous_not_guessed(catalogue):
    terms = ["gasket"]
    candidates = catalogue.shortlist(terms)
    status, winner = catalogue.decide(terms, candidates)
    assert status == "ambiguous" and winner is None and len(candidates) > 1


def test_nonsense_is_unmatched(catalogue):
    terms = ["zzqx wibble"]
    status, winner = catalogue.decide(terms, catalogue.shortlist(terms))
    assert status == "unmatched" and winner is None


def test_shortlist_is_sorted_and_bounded(catalogue):
    out = catalogue.shortlist(["gate valve", "valve gate"], limit=5)
    assert len(out) <= 5
    assert [c.score for c in out] == sorted((c.score for c in out), reverse=True)


def test_by_code_roundtrip(catalogue):
    hit = catalogue.exact("gate valves")
    assert catalogue.by_code(hit.code).title == hit.title
    assert catalogue.by_code("00000000") is None


def test_rejects_bad_catalogue():
    base = {"commodity_code": ["1", "2"], "commodity_title": ["a", "b"], "class_title": ["", ""], "default_unit": ["Nos", "Nos"]}
    with pytest.raises(CatalogueError):
        Catalogue(pd.DataFrame({**base, "commodity_code": ["1", "1"]}))
    with pytest.raises(CatalogueError):
        Catalogue(pd.DataFrame({**base, "default_unit": ["Nos", "Bundle"]}))
    with pytest.raises(CatalogueError):
        Catalogue(pd.DataFrame({"commodity_code": ["1"]}))


def test_normalize():
    assert normalize("  Gate-Valve, (2\") ") == "gate valve 2"
