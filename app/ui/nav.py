"""App-controlled navigation: pill tabs that buttons elsewhere in the flow can also drive."""

import streamlit as st

PAGES = ("Generate an RFQ", "Manage My RFQs", "Evaluate Quotations")
KEY = "nav_page"


def current() -> str:
    return st.session_state.get(KEY) or PAGES[0]


def go(page: str) -> None:
    """Jump to a screen. Use as an on_click callback so the widget value can be set safely."""
    st.session_state[KEY] = page


def _on_change() -> None:
    # Clicking the active pill clears the control; keep the page the user was on.
    if st.session_state.get(KEY) is None:
        st.session_state[KEY] = st.session_state.get("_last_page", PAGES[0])


def render() -> str:
    st.session_state.setdefault(KEY, PAGES[0])
    st.segmented_control(
        "Navigation", PAGES, selection_mode="single", key=KEY, label_visibility="collapsed", on_change=_on_change
    )
    page = current()
    st.session_state["_last_page"] = page
    return page
