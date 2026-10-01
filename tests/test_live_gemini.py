"""LiveGemini against a scripted fake SDK client: no network, no key, no quota."""

import json
from types import SimpleNamespace

import pytest
from google.genai import errors

from app import config, state
from app.schemas.llm import ResolveRequest
from app.schemas.rfq import CatalogueCandidate
from app.services import gemini_client as gc
from app.services import rfq_service
from app.services.catalogue_service import Catalogue

PARSE_OK = {
    "input_class": "procurement_request",
    "global_question": None,
    "items": [
        {"original_text": "4 gate valves", "item_phrase": "gate valves", "search_terms": ["gate valve"],
         "quantity_text": "4", "unit_text": None, "question": None}
    ],
}


def response(payload, finish="STOP"):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(text=text, candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name=finish))])


class FakeModels:
    def __init__(self, script):
        self.script, self.seen = list(script), []

    def generate_content(self, model, contents, config):
        self.seen.append((model, contents))
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def live(script, limit=None):
    client = gc.LiveGemini("test-key", "gemini-2.5-flash-lite", call_limit=limit)
    client._client = SimpleNamespace(models=FakeModels(script))
    return client


def api_error(code):
    return errors.APIError(code, {"error": {"code": code, "message": "x", "status": "X"}})


def test_parse_validates_and_converts_the_wire_schema():
    client = live([response(PARSE_OK)])
    result = client.parse_request("4 gate valves")
    assert result.items[0].item_phrase == "gate valves" and result.items[0].quantity_text == "4"
    model, contents = client._client.models.seen[0]
    assert model == "gemini-2.5-flash-lite" and "<request>" in contents  # request is wrapped as data


def test_truncated_response_is_a_failure_not_a_partial_parse():
    with pytest.raises(gc.BadResponse):
        live([response(PARSE_OK, finish="MAX_TOKENS")]).parse_request("x")


@pytest.mark.parametrize("raw", ["not json", json.dumps({"input_class": "procurement_request"}), ""])
def test_invalid_output_is_rejected(raw):
    with pytest.raises(gc.BadResponse):
        live([response(raw)]).parse_request("x")


def test_rate_limit_is_not_retried():
    client = live([api_error(429), response(PARSE_OK)])
    with pytest.raises(gc.RateLimited):
        client.parse_request("x")
    assert client.calls == 1


def test_transient_server_error_is_retried_once(monkeypatch):
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)
    client = live([api_error(503), response(PARSE_OK)])
    assert client.parse_request("x").items
    assert client.calls == 2


def test_persistent_server_error_gives_up(monkeypatch):
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)
    client = live([api_error(500), api_error(500)])
    with pytest.raises(gc.GeminiError):
        client.parse_request("x")
    assert client.calls == 2


def test_call_budget_is_enforced():
    client = live([response(PARSE_OK), response(PARSE_OK)], limit=1)
    client.parse_request("x")
    with pytest.raises(gc.CallBudgetExceeded):
        client.parse_request("x")


def test_resolve_is_chunked(monkeypatch):
    monkeypatch.setattr(config, "RESOLVE_BATCH_SIZE", 30)
    cand = CatalogueCandidate(code="1", title="A", class_title="C", score=90)
    requests = [ResolveRequest(item_index=i, original_text="a", item_phrase="a", candidates=[cand]) for i in range(65)]

    def reply(start, stop):
        return response({"resolutions": [
            {"item_index": i, "choice_code": "1", "confidence": "medium", "reason": "ok", "alternatives": []}
            for i in range(start, stop)]})

    client = live([reply(0, 30), reply(30, 60), reply(60, 65)])
    result = client.resolve_items(requests)
    assert client.calls == 3 and len(result.resolutions) == 65


def test_prompts_carry_the_key_rules():
    parse = (gc.PROMPTS / "rfq_parse.md").read_text()
    assert "never infer" in parse.lower() and "<request>" in parse and "verbatim" in parse
    resolve = (gc.PROMPTS / "catalogue_resolve.md").read_text()
    assert "never invent a code" in resolve.lower()


def test_rate_limit_becomes_a_friendly_message():
    class Limited:
        def parse_request(self, text):
            raise gc.RateLimited("x")

        def resolve_items(self, requests):
            raise gc.RateLimited("x")

    store: dict = {}
    state.init_state(store)
    result = rfq_service.build_draft("4 gate valves", Limited(), Catalogue.load(), store)
    assert "rate limit" in result.error.lower() and store.get("last_failed_input") is None  # retry allowed


def test_mock_is_used_without_a_key(monkeypatch):
    monkeypatch.setattr(config, "get_api_key", lambda: None)
    assert isinstance(gc.get_client(), gc.MockGemini)


def test_suite_cannot_reach_the_live_api():
    assert config.get_api_key() in (None, "") and not config.MODEL_LITE
    assert isinstance(gc.get_client(), gc.MockGemini)
