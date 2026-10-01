from collections.abc import MutableMapping
from typing import Any


import streamlit as st

from app import config, state
from app.services import rfq_service
from app.services.catalogue_service import Catalogue
from app.ui import loader, resources, rfq_review, rfq_table
from app.ui import rfq_actions as actions
from app.ui.components import notice

PLACEHOLDER = "e.g. 4 pressure transmitters, 20 m instrument cable, 2 pairs of safety gloves"
INTRO = "Describe what you need in your own words. Items, quantities and units are extracted for you to review. Press Enter to send."


def _start(store: MutableMapping[str, Any], text: str) -> None:
    """A request was sent: remember it and redraw the page as the loading layout."""
    store["rfq_request"] = text
    store["building"] = text
    st.rerun()


def _render_building(store: MutableMapping[str, Any], text: str, catalogue: Catalogue) -> None:
    """Loading layout: the request, read-only, where the input box is; progress where the Review summary will be."""
    st.subheader("Generate an RFQ")
    left, right = st.columns([2, 3], gap="large")
    with left:
        st.text_area("Your request", value=text, height=150, disabled=True, label_visibility="collapsed",
                     key="building-text")
    with right:
        with st.container(border=True, key="card-loading"):
            slot = st.empty()
    store.pop("building", None)  # first, so an interrupted run does not loop
    result = rfq_service.build_draft(text, resources.client(), catalogue, store, progress=loader.make_callback(slot))
    if result.rfq:
        store["rfq_draft"] = result.rfq
        store["rfq_notice"] = None
        st.session_state[actions.NAME_KEY] = result.rfq.name
    else:
        store["rfq_notice"] = {"unclear": result.unclear, "message": result.error}
    st.rerun()


def _render_notice(store: MutableMapping[str, Any]) -> None:
    info = store.get("rfq_notice")
    if not info:
        return
    if info["unclear"]:
        notice("warn", info["message"], " Try listing the products you need, with quantities and units if you have them.")
        st.caption(f"For example: {rfq_service.EXAMPLE_REQUEST}")
        st.button("Use this example", on_click=actions.use_example, args=(store,), key="use-example")
    else:
        notice("error", info["message"])


def render(store: MutableMapping[str, Any]) -> None:
    catalogue = resources.load_catalogue_or_none()
    if catalogue is None:
        notice("error", "The item catalogue could not be loaded.", " RFQs cannot be created right now.")
        return

    draft = store.get("rfq_draft")
    if draft is not None and draft.status == "saved":
        rfq_table.render(store, draft, editable=False)
        return

    if store.get("building"):
        _render_building(store, store["building"], catalogue)
        return
    pending = store.pop("pending_prompt", None)

    st.subheader("Generate an RFQ")
    if draft is None:
        st.write(INTRO)
        with st.columns(1)[0]:  # a chat input at the top level, or in a plain container, pins to the page bottom
            typed = st.chat_input(PLACEHOLDER, max_chars=config.MAX_INPUT_CHARS, key="rfq_chat")
        notice_slot = st.container()
        prompt = pending or typed
        if prompt:
            _start(store, prompt)
        with notice_slot:
            _render_notice(store)
        return

    left, right = st.columns([2, 3], gap="large")
    with left:
        with st.container(border=True, key="card-request"):
            st.markdown("<span class='th'>Your request</span>", unsafe_allow_html=True)
            request = store.get("rfq_request", "")
            with st.container(height=150 if len(request) > 220 else "content", border=False):
                st.write(request)
        typed = st.chat_input(PLACEHOLDER, max_chars=config.MAX_INPUT_CHARS, key="rfq_chat")
        notice_slot = st.container()
    prompt = pending or typed
    if prompt:
        _start(store, prompt)
    with notice_slot:
        _render_notice(store)
    with right:
        rfq_review.render(draft)
    st.write("")
    rfq_table.render(store, draft)
