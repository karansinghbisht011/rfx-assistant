"""Step bar for Evaluate Quotations: Select RFQ, Upload, Review, Compare (the analyst lives in Compare)."""

from collections.abc import MutableMapping
from typing import Any

import streamlit as st

STEPS = ("Select RFQ", "Upload", "Review", "Compare")
LIVE_STEPS = 4
KEY = "eval_step"


def current(store: MutableMapping[str, Any]) -> int:
    return int(store.get(KEY) or 1)


def go(store: MutableMapping[str, Any], step: int) -> None:
    store[KEY] = max(1, min(step, len(STEPS)))


def render(store: MutableMapping[str, Any], unlocked: int) -> None:
    """Show the five steps: done, active, available, or locked. Display only; Back/Next move between them."""
    step = current(store)
    chips = []
    for n, label in enumerate(STEPS, start=1):
        if n == step:
            state = "active"
        elif n < step:
            state = "done"
        elif n <= unlocked and n <= LIVE_STEPS:
            state = "open"
        else:
            state = "locked"
        mark = "✓" if state == "done" else str(n)
        chips.append(f"<div class='step step-{state}'><span class='step-n'>{mark}</span>{label}</div>")
        if n < len(STEPS):
            chips.append(f"<div class='step-line step-line-{'done' if n < step else 'todo'}'></div>")
    st.markdown(f"<div class='stepper'>{''.join(chips)}</div>", unsafe_allow_html=True)
