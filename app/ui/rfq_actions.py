"""Callbacks for the RFQ tab. They change the RFQ object; Streamlit then reruns the page."""

from collections.abc import MutableMapping
from typing import Any

import streamlit as st

from app.schemas.rfq import RFQ, CatalogueCandidate
from app.services import rfq_service

NAME_KEY = "rfq_name"


def on_qty(rfq: RFQ, item_id: str, key: str) -> None:
    rfq_service.set_quantity(rfq, item_id, st.session_state.get(key))


def on_unit(rfq: RFQ, item_id: str, key: str) -> None:
    rfq_service.set_unit(rfq, item_id, st.session_state.get(key))


def on_pick(rfq: RFQ, item_id: str, candidate: CatalogueCandidate) -> None:
    rfq_service.pick_catalogue_item(rfq, item_id, candidate)
    for state in ("bad", "sug", "ok"):  # the unit may have changed; recreate its widget from the item
        st.session_state.pop(f"unit-{state}-{item_id}", None)
    st.session_state[f"search-{item_id}"] = ""
    st.toast(f"Item set to {candidate.title}", icon=":material/check_circle:")


def on_remove(rfq: RFQ, item_id: str) -> None:
    rfq_service.remove_item(rfq, item_id)


def on_accept(rfq: RFQ, scope_id: str, code: str) -> None:
    rfq_service.acknowledge(rfq, scope_id, code)


def on_name(rfq: RFQ) -> None:
    rfq.name = st.session_state[NAME_KEY]


def on_save(store: MutableMapping[str, Any], rfq: RFQ) -> None:
    rfq_service.finalize(store, rfq)


def on_new(store: MutableMapping[str, Any]) -> None:
    store["rfq_draft"] = None
    store["rfq_notice"] = None
    store["rfq_request"] = ""


def use_example(store: MutableMapping[str, Any]) -> None:
    store["pending_prompt"] = rfq_service.EXAMPLE_REQUEST
