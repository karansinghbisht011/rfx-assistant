"""'Your RFQ': header (name, save, download) and the table of lines, review items first."""

import streamlit as st

from app import config
from app.schemas.rfq import RFQ, RequestedItem
from app.services import pdf_service, rfq_service, verifiers
from app.services.quantities import format_quantity
from app.ui import rfq_actions as actions
from app.ui import nav, rfq_picker

COLUMNS = [0.35, 4.2, 1.35, 1.6, 2.3, 1.3, 0.5]


def _has(item: RequestedItem, code: str) -> bool:
    return any(f.open and f.code == code for f in item.flags)


def row_state(item: RequestedItem) -> str:
    """fix: must edit; review: needs a decision; hint: a suggestion was applied; ok: confirmed."""
    if verifiers.is_blocking(item):
        return "fix"
    if verifiers.needs_review(item):
        return "review"
    if item.unit_suggested or (item.match_status == "fuzzy" and not item.buyer_selected):
        return "hint"
    return "ok"


def _chips(item: RequestedItem) -> str:
    chips = []
    for flag in item.flags:
        if flag.open and flag.severity in ("block", "review"):
            colour = "red" if flag.code in ("R6", "R8") else "orange"
            chips.append(f":{colour}-badge[{verifiers.short_label(flag)}]")
    if item.match_status == "fuzzy" and not item.buyer_selected and not chips:
        chips.append(":blue-badge[Close match]")
    if item.unit_suggested:
        chips.append(":blue-badge[Unit suggested]")
    return " ".join(chips) or ":green-badge[Confirmed]"


def _header(rfq: RFQ, editable: bool, store) -> None:
    review = sum(1 for i in rfq.items if verifiers.needs_review(i))
    title, name, action = st.columns([2.2, 2.2, 3.6] if not editable else [2.4, 2.6, 2.2], vertical_alignment="center")
    sub = f"{len(rfq.items)} item{'s' if len(rfq.items) != 1 else ''}"
    sub += f" · {review} need review" if review else " · all confirmed"
    title.markdown(f"<div class='rfq-title'>Your RFQ</div><div class='rfq-sub'>{sub}</div>", unsafe_allow_html=True)
    name.text_input(
        "RFQ name", key=actions.NAME_KEY, placeholder="RFQ name", label_visibility="collapsed",
        on_change=actions.on_name, args=(rfq,), disabled=not editable,
    )
    if editable:
        label = "Save RFQ" if verifiers.can_save(rfq) else f"Resolve {len(verifiers.open_flags(rfq))} to save"
        action.button(label, type="primary", disabled=not verifiers.can_save(rfq), use_container_width=True,
                      on_click=actions.on_save, args=(store, rfq), key="save-rfq")
    else:
        left, middle, right = action.columns([1.2, 1.6, 1])
        left.download_button("Download PDF", data=pdf_service.build_rfq_pdf(rfq), file_name=f"{rfq.name}.pdf",
                             mime="application/pdf", type="primary", use_container_width=True)
        middle.button("View in Manage RFQs", on_click=nav.go, args=("Manage My RFQs",), use_container_width=True)
        right.button("New RFQ", on_click=actions.on_new, args=(store,), use_container_width=True)


def _row(number: int, item: RequestedItem, rfq: RFQ, editable: bool) -> None:
    state = row_state(item)
    with st.container(key=f"row-{state}-{item.item_id}-{item.catalogue_code or 'none'}"):
        num, name, qty, unit, status, pick, remove = st.columns(COLUMNS, vertical_alignment="center")
        num.caption(str(number))
        name.markdown(f"**{item.catalogue_title or item.original_text}**")
        if item.catalogue_title:
            name.caption(f"You wrote: {item.original_text}")
        status.markdown(_chips(item))
        if not editable:
            qty.write(format_quantity(item.quantity))
            unit.write(item.unit or "")
            return
        qty_key = f"qty-{'bad' if _has(item, 'R6') else 'ok'}-{item.item_id}"
        qty.number_input(
            "Quantity", value=float(item.quantity) if item.quantity is not None else None, min_value=0.0,
            step=1.0, format="%g", key=qty_key, label_visibility="collapsed",
            on_change=actions.on_qty, args=(rfq, item.item_id, qty_key),
        )
        flavour = "bad" if _has(item, "R8") else "sug" if item.unit_suggested else "ok"
        unit_key = f"unit-{flavour}-{item.item_id}"
        unit.selectbox(
            "Unit", options=list(config.CANONICAL_UNITS),
            index=config.CANONICAL_UNITS.index(item.unit) if item.unit in config.CANONICAL_UNITS else None,
            placeholder="Unit", key=unit_key, label_visibility="collapsed",
            on_change=actions.on_unit, args=(rfq, item.item_id, unit_key),
        )
        rfq_picker.render(pick, item, lambda item_id, candidate, rfq=rfq: actions.on_pick(rfq, item_id, candidate))
        remove.button("", icon=":material/delete:", key=f"remove-{item.item_id}", help="Remove this line",
                      on_click=actions.on_remove, args=(rfq, item.item_id))


def render(store, rfq: RFQ, editable: bool = True) -> None:
    _header(rfq, editable, store)
    if not rfq.items:
        st.info("All lines were removed. Send a new request to start again.")
        return
    cols = st.columns(COLUMNS)
    for col, label in zip(cols, ["#", "Item", "Quantity", "Unit", "Status", "", ""]):
        col.markdown(f"<span class='th'>{label}</span>", unsafe_allow_html=True)
    for number, item in enumerate(rfq_service.ordered_items(rfq), start=1):
        _row(number, item, rfq, editable)
