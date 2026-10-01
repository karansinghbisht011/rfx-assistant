from collections.abc import MutableMapping
from typing import Any

import streamlit as st


def render(store: MutableMapping[str, Any]) -> None:
    st.subheader("Generate an RFQ")
    st.write("Describe what you need in your own words. Items, quantities and units are extracted for you to review.")

    st.text_area(
        "Procurement request",
        placeholder="e.g. 4 pressure transmitters, 20 m instrument cable, 2 pairs of safety gloves",
        height=140,
        disabled=True,
    )
    st.button("Create RFQ", type="primary", disabled=True)
