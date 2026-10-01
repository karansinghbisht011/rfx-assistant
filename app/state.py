"""Session state helpers.

Pure functions over a MutableMapping so they can be tested with a plain dict;
the app passes st.session_state. Nothing here persists beyond the session.
"""

from collections.abc import MutableMapping
from typing import Any

from app import config
from app.ids import new_id
from app.schemas.analysis import Assumptions
from app.schemas.rfq import RFQ

TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "rfq": {
        "draft": {"ready"},
        "ready": {"draft", "saved"},
        "saved": set(),
    },
    "quotation": {
        "uploaded": {"parsed", "rejected"},
        "parsed": {"needs_review", "validated", "rejected"},
        "needs_review": {"validated", "rejected"},
        "validated": {"needs_review"},
        "rejected": set(),
    },
    "analysis": {
        "not_started": {"processing"},
        "processing": {"needs_review", "complete", "failed"},
        "needs_review": {"complete", "processing"},
        "complete": {"processing"},
        "failed": {"processing"},
    },
}


class InvalidTransition(ValueError):
    pass


class CallLimitReached(RuntimeError):
    """Session Gemini call cap reached (verifier R16)."""


def check_transition(kind: str, old: str, new: str) -> None:
    if new not in TRANSITIONS[kind].get(old, set()):
        raise InvalidTransition(f"{kind}: cannot move from '{old}' to '{new}'")


def init_state(store: MutableMapping[str, Any]) -> None:
    """Create any missing keys. Safe to call on every rerun."""
    defaults = {
        "session_id": new_id("session"),
        "rfqs": {},                      # rfq_id -> RFQ
        "rfq_draft": None,
        "selected_rfq_id": None,
        "quotations": {},                # quotation_id -> Quotation
        "analysis_status": "not_started",
        "assumptions": Assumptions(),
        "analyst_history": [],
        "gemini_calls": 0,
    }
    for key, value in defaults.items():
        store.setdefault(key, value)


def save_rfq(store: MutableMapping[str, Any], rfq: RFQ) -> RFQ:
    """Move a ready RFQ to saved and keep it for this session."""
    check_transition("rfq", rfq.status, "saved")
    rfq.status = "saved"
    rfq.source_session_id = store["session_id"]
    store["rfqs"][rfq.rfq_id] = rfq
    return rfq


def list_rfqs(store: MutableMapping[str, Any]) -> list[RFQ]:
    return sorted(store["rfqs"].values(), key=lambda r: r.created_at, reverse=True)


def select_rfq(store: MutableMapping[str, Any], rfq_id: str) -> RFQ:
    if rfq_id not in store["rfqs"]:
        raise KeyError(f"No saved RFQ with id {rfq_id}")
    store["selected_rfq_id"] = rfq_id
    return store["rfqs"][rfq_id]


def selected_rfq(store: MutableMapping[str, Any]) -> RFQ | None:
    return store["rfqs"].get(store["selected_rfq_id"])


def record_gemini_call(store: MutableMapping[str, Any]) -> int:
    """Count a Gemini call against the session cap; raise once the cap is reached."""
    if store["gemini_calls"] >= config.MAX_CALLS_PER_SESSION:
        raise CallLimitReached(f"Session limit of {config.MAX_CALLS_PER_SESSION} AI calls reached")
    store["gemini_calls"] += 1
    return store["gemini_calls"]
