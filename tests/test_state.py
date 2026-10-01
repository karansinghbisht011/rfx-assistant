import pytest

from app import config, state
from app.schemas.rfq import RFQ


def make_store():
    store: dict = {}
    state.init_state(store)
    return store


def test_init_state_is_idempotent():
    store = make_store()
    session_id = store["session_id"]
    state.init_state(store)
    assert store["session_id"] == session_id
    assert store["rfqs"] == {}


def test_save_rfq_requires_ready_and_stores_it():
    store = make_store()
    rfq = RFQ(name="RFQ-2026-10-01")
    with pytest.raises(state.InvalidTransition):
        state.save_rfq(store, rfq)  # still a draft
    rfq.status = "ready"
    state.save_rfq(store, rfq)
    assert rfq.status == "saved"
    assert rfq.source_session_id == store["session_id"]
    assert state.list_rfqs(store) == [rfq]


def test_select_rfq():
    store = make_store()
    rfq = RFQ(name="a", status="ready")
    state.save_rfq(store, rfq)
    state.select_rfq(store, rfq.rfq_id)
    assert state.selected_rfq(store) is rfq
    with pytest.raises(KeyError):
        state.select_rfq(store, "rfq-missing")


@pytest.mark.parametrize(
    "kind,old,new,ok",
    [
        ("rfq", "draft", "ready", True),
        ("rfq", "draft", "saved", False),
        ("rfq", "saved", "draft", False),
        ("quotation", "uploaded", "parsed", True),
        ("quotation", "uploaded", "validated", False),
        ("quotation", "needs_review", "validated", True),
        ("quotation", "rejected", "parsed", False),
        ("analysis", "not_started", "processing", True),
        ("analysis", "not_started", "complete", False),
        ("analysis", "failed", "processing", True),
    ],
)
def test_transitions(kind, old, new, ok):
    if ok:
        state.check_transition(kind, old, new)
    else:
        with pytest.raises(state.InvalidTransition):
            state.check_transition(kind, old, new)


def test_call_cap(monkeypatch):
    monkeypatch.setattr(config, "MAX_CALLS_PER_SESSION", 2)
    store = make_store()
    state.record_gemini_call(store)
    state.record_gemini_call(store)
    with pytest.raises(state.CallLimitReached):
        state.record_gemini_call(store)
