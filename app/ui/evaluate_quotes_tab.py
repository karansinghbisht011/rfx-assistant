from collections.abc import MutableMapping
from typing import Any

import streamlit as st

from app import state
from app.ui.components import empty_state


def render(store: MutableMapping[str, Any]) -> None:
    st.subheader("Evaluate Quotations")
    if not state.list_rfqs(store):
        empty_state(
            "Save an RFQ first",
            "Quotations are evaluated against an RFQ saved in this session. Create one in Generate an RFQ.",
        )
        return
    st.write("Select an RFQ, then upload vendor quotations to compare.")
    st.file_uploader(
        "Vendor quotations",
        type=["csv", "tsv", "xlsx", "pdf", "docx"],
        accept_multiple_files=True,
        disabled=True,
    )
