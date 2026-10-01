from collections.abc import MutableMapping
from typing import Any

import streamlit as st

from app import state
from app.schemas.rfq import RFQ
from app.services import pdf_service
from app.services.quantities import format_quantity
from app.ui import nav
from app.ui.components import empty_state

COLUMNS = [2.6, 2.8, 1.9, 5.4]


def _toggle_view(rfq_id: str) -> None:
    key = f"view-{rfq_id}"
    st.session_state[key] = not st.session_state.get(key, False)


def _select(store: MutableMapping[str, Any], rfq_id: str) -> None:
    state.select_rfq(store, rfq_id)
    nav.go("Evaluate Quotations")


def _stats(rfqs: list[RFQ]) -> str:
    total_items = sum(len(r.items) for r in rfqs)
    latest = max(r.created_at for r in rfqs).strftime("%d %b, %H:%M")
    tiles = [("RFQs saved", str(len(rfqs))), ("Line items", str(total_items)), ("Latest", latest)]
    return "".join(f"<div class='stat'><div class='stat-n'>{n}</div><div class='stat-l'>{label}</div></div>" for label, n in tiles)


def _preview(rfq: RFQ) -> str:
    names = [i.catalogue_title or i.original_text for i in rfq.items]
    shown = ", ".join(names[:3])
    return shown + (f" +{len(names) - 3} more" if len(names) > 3 else "")


def _status(rfq: RFQ, selected: bool) -> str:
    reviewed = sum(1 for e in rfq.review_log if e.status == "reviewed")
    fixed = sum(1 for e in rfq.review_log if e.status == "fixed")
    chips = [":green-badge[Saved]"]
    if fixed:
        chips.append(f":blue-badge[{fixed} fixed]")
    if reviewed:
        chips.append(f":violet-badge[{reviewed} accepted]")
    if selected:
        chips.append(":primary-badge[Selected]")
    return " ".join(chips)


def _row(store: MutableMapping[str, Any], rfq: RFQ) -> None:
    selected = store.get("selected_rfq_id") == rfq.rfq_id
    with st.container(key=f"row-{'hint' if selected else 'ok'}-{rfq.rfq_id}"):
        name, items, status, actions = st.columns(COLUMNS, vertical_alignment="center")
        name.markdown(f"**{rfq.name}**")
        name.caption(f"Created {rfq.created_at.strftime('%d %b %Y, %H:%M')} · {rfq.rfq_id}")
        count = len(rfq.items)
        items.markdown(f"**{count} item{'s' if count != 1 else ''}**")
        items.caption(_preview(rfq))
        status.markdown(_status(rfq, selected))
        view, download, select = actions.columns([0.8, 0.9, 2.4])
        viewing = st.session_state.get(f"view-{rfq.rfq_id}", False)
        view.button("Hide" if viewing else "View", key=f"vbtn-{rfq.rfq_id}", on_click=_toggle_view,
                    args=(rfq.rfq_id,), use_container_width=True)
        download.download_button("PDF", data=pdf_service.build_rfq_pdf(rfq), file_name=f"{rfq.name}.pdf",
                                mime="application/pdf", key=f"dl-{rfq.rfq_id}", use_container_width=True)
        select.button("Select for evaluation", key=f"sel-{rfq.rfq_id}", type="primary", on_click=_select,
                      args=(store, rfq.rfq_id), use_container_width=True)
        if viewing:
            st.dataframe(
                [
                    {"#": n, "Item": i.catalogue_title or i.original_text, "Quantity": format_quantity(i.quantity),
                     "Unit": i.unit or "", "You wrote": i.original_text}
                    for n, i in enumerate(rfq.items, start=1)
                ],
                hide_index=True, use_container_width=True,
            )


def render(store: MutableMapping[str, Any]) -> None:
    st.subheader("Manage My RFQs")
    rfqs = state.list_rfqs(store)
    if not rfqs:
        empty_state("No RFQs yet", "RFQs you save in this session appear here. Create one in Generate an RFQ.")
        return
    st.markdown(f"<div class='stats'>{_stats(rfqs)}</div>", unsafe_allow_html=True)
    head = st.columns(COLUMNS)
    for col, label in zip(head, ["RFQ", "Items", "Status", "Actions"]):
        col.markdown(f"<span class='th'>{label}</span>", unsafe_allow_html=True)
    for rfq in rfqs:
        _row(store, rfq)
