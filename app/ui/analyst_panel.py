"""The analyst chat on the Compare page: ask in plain language, and the proposal appears on the left."""

import html
from collections.abc import MutableMapping
from decimal import Decimal
from typing import Any

import streamlit as st

from app import config, state
from app.schemas.analyst import AnalystTurn
from app.schemas.quotation import Quotation
from app.schemas.rfq import RFQ
from app.services import analyst_service
from app.ui import proposal_view, resources

def turns(store: MutableMapping[str, Any]) -> list[AnalystTurn]:
    return store.setdefault("analyst_turns", [])


def _disabled_reason(store) -> str | None:
    if getattr(resources.client(), "stand_in", False):
        return "Add a Gemini key to use the analyst"
    if store.get("gemini_calls", 0) >= config.MAX_CALLS_PER_SESSION:
        return "The AI call limit for this session has been reached"
    return None


def _working(slot) -> None:
    slot.markdown("<div class='chat-working'><b>Working on it</b><div class='an-bar'><div class='an-bar-fill' style='width:60%'></div></div>"
                  "<div class='an-sub'>Reading your request · finding the cheapest purchase · checking the rules</div></div>",
                  unsafe_allow_html=True)


def _thread(store, box) -> None:
    with box:
        history = turns(store)
        for t in history:
            with st.chat_message("user"):
                st.write(t.question)
            with st.chat_message("assistant"):
                st.write(t.reply)
                if t.proposal:
                    chips = "".join(f"<span class='chat-chip {'met' if r.met else 'unmet'}'>{'✓' if r.met else '!'} {html.escape(r.text)}</span>"
                                    for r in t.proposal.rules)
                    st.markdown(chips, unsafe_allow_html=True)


def render(store: MutableMapping[str, Any], rfq: RFQ, kept: list[Quotation], rates: dict[str, Decimal]) -> None:
    """Draw the thread and input, and answer a new request. Call this before drawing the proposal so it shows the answer."""
    proposal_view.heading("Analyst", "Ask for a purchase proposal in plain language")
    box = st.container(height=470, border=True)
    reason = _disabled_reason(store)
    prompt = st.chat_input(reason or "Describe the purchase you want", disabled=reason is not None, key="analyst-input",
                           max_chars=config.ANALYST_MAX_QUESTION_CHARS)
    if prompt and not reason:
        with box:
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant"):
                slot = st.empty()
                _working(slot)
                turn = analyst_service.run_turn(store, rfq, kept, prompt, resources.client(), rates, turns(store))
                slot.empty()
        history = turns(store)
        history.append(turn)
        del history[:-20]
        st.rerun()   # redraw the whole page so the proposal on the left shows the answer
    _thread(store, box)
