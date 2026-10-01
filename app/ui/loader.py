"""Animated progress shown while an RFQ is built. Steps follow real service milestones."""

import html

import streamlit as st

STEPS = [
    ("read", "Reading your request"),
    ("match", "Matching items against the catalogue"),
    ("choose", "Choosing the best matches"),
    ("prepare", "Preparing your RFQ"),
]


def _render(current: str) -> str:
    keys = [k for k, _ in STEPS]
    position = keys.index(current)
    items = []
    for index, (_, label) in enumerate(STEPS):
        state = "done" if index < position else "active" if index == position else ""
        items.append(f"<li class='{state}'><span class='dot'></span>{html.escape(label)}</li>")
    return (
        "<div class='loader-title'>Building your RFQ</div><div class='loader-bar'></div>"
        f"<ul class='loader-steps'>{''.join(items)}</ul>"
    )


def make_callback(slot):
    """Return a progress(stage) function that redraws the steps inside the given st.empty() slot."""

    def progress(stage: str) -> None:
        if any(stage == key for key, _ in STEPS):
            slot.markdown(_render(stage), unsafe_allow_html=True)

    return progress
