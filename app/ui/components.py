import html
import re

import streamlit as st


def empty_state(title: str, body: str) -> None:
    # The "card-" key prefix is what theme.py styles.
    key = "card-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    with st.container(border=True, key=key):
        st.markdown(f"**{title}**")
        st.write(body)


def notice(kind: str, title: str, body: str = "") -> None:
    """A coloured message card. kind is one of warn, error, info, ok."""
    text = f"<div class='notice notice-{kind}'><b>{html.escape(title)}</b>{html.escape(body)}</div>"
    st.markdown(text, unsafe_allow_html=True)
