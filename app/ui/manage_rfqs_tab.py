from collections.abc import MutableMapping
from typing import Any

import streamlit as st

from app import state
from app.ui.components import empty_state


def render(store: MutableMapping[str, Any]) -> None:
    st.subheader("Manage My RFQs")
    rfqs = state.list_rfqs(store)
    if not rfqs:
        empty_state("No RFQs yet", "RFQs you save in this session appear here. Create one in Generate an RFQ.")
        return
    st.dataframe(
        [{"Name": r.name, "Created": r.created_at.strftime("%d %b %Y"), "Items": len(r.items)} for r in rfqs],
        hide_index=True,
        use_container_width=True,
    )
