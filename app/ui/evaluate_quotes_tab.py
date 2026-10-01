from collections.abc import MutableMapping
from typing import Any

import streamlit as st

from app import state
from app.schemas.rfq import RFQ
from app.ui import nav
from app.ui.components import empty_state


def _preview(rfq: RFQ) -> str:
    names = [i.catalogue_title or i.original_text for i in rfq.items]
    return ", ".join(names[:4]) + (f" +{len(names) - 4} more" if len(names) > 4 else "")


def _choose(store: MutableMapping[str, Any]) -> None:
    rfq_id = st.session_state.get("eval-rfq-select")
    if rfq_id:
        state.select_rfq(store, rfq_id)


def _selected_card(store: MutableMapping[str, Any], rfq: RFQ) -> None:
    """The RFQ being evaluated: name, date, size, a preview of its items, and a way to change it."""
    with st.container(key="row-hint-evaluating"):
        info, items, action = st.columns([3, 4.6, 1.7], vertical_alignment="center")
        info.markdown(f"**{rfq.name}** :primary-badge[Evaluating]")
        info.caption(f"Created {rfq.created_at.strftime('%d %b %Y, %H:%M')}")
        count = len(rfq.items)
        items.markdown(f"**{count} item{'s' if count != 1 else ''}**")
        items.caption(_preview(rfq))
        action.button("Change RFQ", key="change-rfq", on_click=nav.go, args=("Manage My RFQs",), use_container_width=True)


def _chooser(store: MutableMapping[str, Any], rfqs: list[RFQ]) -> None:
    with st.container(border=True, key="card-choose-rfq"):
        st.markdown("**Choose the RFQ to evaluate**")
        st.selectbox(
            "RFQ", options=[r.rfq_id for r in rfqs], index=None, placeholder="Pick one of your saved RFQs",
            format_func=lambda rfq_id: next(f"{r.name}  ·  {len(r.items)} items" for r in rfqs if r.rfq_id == rfq_id),
            key="eval-rfq-select", label_visibility="collapsed", on_change=_choose, args=(store,),
        )


def render(store: MutableMapping[str, Any]) -> None:
    st.subheader("Evaluate Quotations")
    rfqs = state.list_rfqs(store)
    if not rfqs:
        empty_state(
            "Save an RFQ first",
            "Quotations are evaluated against an RFQ saved in this session. Create one in Generate an RFQ.",
        )
        return
    chosen = state.selected_rfq(store)
    if chosen:
        _selected_card(store, chosen)
    else:
        _chooser(store, rfqs)
    st.write("Upload vendor quotations to compare against this RFQ.")
    st.file_uploader(
        "Vendor quotations",
        type=["csv", "tsv", "xlsx", "pdf", "docx"],
        accept_multiple_files=True,
        disabled=True,
    )
