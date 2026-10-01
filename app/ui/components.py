import re

import streamlit as st


def empty_state(title: str, body: str) -> None:
    # The "card-" key prefix is what theme.py styles.
    key = "card-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    with st.container(border=True, key=key):
        st.markdown(f"**{title}**")
        st.write(body)
