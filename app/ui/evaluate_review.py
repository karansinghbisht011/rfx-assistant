"""Review step: how each quotation lines up with the RFQ, and what needs the buyer's attention.

The buyer can only Accept a flag or Exclude a line or quotation; no extracted number is ever edited.
"""

import html
from collections.abc import MutableMapping
from decimal import Decimal
from typing import Any

import streamlit as st

from app.schemas.quotation import Quotation, QuotedLineItem
from app.schemas.rfq import RFQ, RequestedItem
from app.services import quote_service, quote_verifiers as qv, units
from app.ui import resources

SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}
COLUMNS = [3.5, 1.3, 1.3, 1.4, 1.2, 1.1]


def usable(store: MutableMapping[str, Any]) -> list[Quotation]:
    return [q for q in quote_service.quotes_of(store) if q.status not in ("rejected", "failed")]


def price_label(line: QuotedLineItem) -> str:
    price = line.price_per_unit
    if price is None:
        return "no price"
    amount = f"{price:,.0f}" if price == price.to_integral_value() else f"{price:,.2f}"
    return f"{SYMBOLS.get(line.currency or '', (line.currency + ' ') if line.currency else '')}{amount}"


def item_lines(quote: Quotation, item: RequestedItem) -> list[QuotedLineItem]:
    return [l for l in quote.lines if l.matched_rfq_item_id == item.item_id and l.match_status in ("matched", "possible")]


def cell(quote: Quotation, item: RequestedItem) -> tuple[str, str, str]:
    """(css class, label, tooltip) for one RFQ item against one quotation."""
    lines = item_lines(quote, item)
    live = [l for l in lines if not l.excluded]
    if not lines:
        return "missing", "not quoted", "This vendor did not quote this item."
    if not live:
        return "excluded", "excluded", "You excluded this line."
    if len(live) > 1:
        return "options", f"{len(live)} options", "Keep one by excluding the others."
    line = live[0]
    if line.unit_price is None:
        return "missing", "no price", line.remarks or "The vendor gave no price."
    open_codes = [f.code for f in line.flags if f.open]
    if open_codes:
        css = "possible" if line.match_status == "possible" and set(open_codes) <= {"M2", "M3"} else "review"
        return css, price_label(line), "Needs review: " + ", ".join(open_codes)
    return "ok", price_label(line), "Matches your RFQ."


def covered(quote: Quotation, rfq: RFQ) -> int:
    return sum(1 for item in rfq.items if any(l.unit_price is not None and not l.excluded for l in item_lines(quote, item)))


def money(amount: Decimal, currency: str | None) -> str:
    symbol = SYMBOLS.get(currency or "", f"{currency} " if currency else "")
    return f"{symbol}{amount:,.0f}"


def totals(quote: Quotation, rfq: RFQ) -> dict[str | None, Decimal]:
    """What the quoted lines come to at the RFQ quantities, per currency, as quoted (no tax or conversion).

    A line counts when it is kept, priced, and in a unit that converts to the RFQ unit. Where a vendor
    gives several options for one item, the lowest is counted."""
    out: dict[str | None, Decimal] = {}
    for item in rfq.items:
        costs: dict[str | None, list[Decimal]] = {}
        for line in item_lines(quote, item):
            price = line.price_per_unit
            if line.excluded or price is None or item.quantity is None:
                continue
            factor = Decimal(1) if not (line.unit and item.unit) else units.convert(Decimal(1), line.unit, item.unit)
            if not factor:
                continue
            costs.setdefault(line.currency, []).append(price / factor * Decimal(str(item.quantity)))
        for currency, values in costs.items():
            out[currency] = out.get(currency, Decimal(0)) + min(values)
    return out


def total_label(quote: Quotation, rfq: RFQ) -> str:
    t = totals(quote, rfq)
    return " + ".join(money(v, c) for c, v in sorted(t.items(), key=lambda p: str(p[0]))) or "no total"


def _tiles(store, rfq: RFQ, quotes: list[Quotation]) -> None:
    complete = sum(1 for q in quotes if covered(q, rfq) == len(rfq.items))
    items_covered = sum(1 for item in rfq.items if any(any(l.unit_price is not None and not l.excluded for l in item_lines(q, item)) for q in quotes))
    review = sum(len(qv.open_flags(q)) for q in quotes)
    data = [("Quotations", len(quotes)), ("RFQ lines quoted", f"{items_covered}/{len(rfq.items)}"),
            ("Complete quotes", complete), ("To review", review)]
    st.markdown("<div class='an-tiles'>" + "".join(
        f"<div class='an-tile'><div class='an-n'>{n}</div><div class='an-l'>{label}</div></div>" for label, n in data) + "</div>",
        unsafe_allow_html=True)


VIEWS = ["Summary", "By item"]


def _set_view(store) -> None:
    choice = st.session_state.get("matrix-view")
    if choice in VIEWS:   # clicking the selected option again clears it; the view then stays as it was
        store["matrix_open"] = choice == VIEWS[1]


def _matrix(store, rfq: RFQ, quotes: list[Quotation]) -> None:
    open_ = store.get("matrix_open", True)
    title, view = st.columns([5, 2.2], vertical_alignment="center")
    title.markdown("**Price comparison**")
    view.segmented_control("View", VIEWS, default=VIEWS[1 if open_ else 0], key="matrix-view", label_visibility="collapsed",
                           on_change=_set_view, args=(store,), width="stretch")
    full = len(rfq.items)
    head = "".join(
        f"<th>{html.escape(q.display_name)}<small>{html.escape(q.source_filename)}</small>"
        f"<span class='cov {'' if covered(q, rfq) == full else 'cov-part'}'>{covered(q, rfq)}/{full} quoted</span>"
        f"<span class='tot'>{html.escape(total_label(q, rfq))}</span></th>"
        for q in quotes)
    body = []
    for item in rfq.items if open_ else []:
        cells = "".join(
            f"<td><span class='mx mx-{css}' title='{html.escape(tip)}'>{html.escape(label)}</span></td>"
            for css, label, tip in (cell(q, item) for q in quotes))
        qty = f"{item.quantity:g} {item.unit}" if item.quantity is not None else ""
        body.append(f"<tr><td class='item'>{html.escape(item.catalogue_title or item.original_text)}<small>{qty}</small></td>{cells}</tr>")
    st.markdown(
        f"<div class='matrix-wrap'><table class='matrix'><thead><tr><th>RFQ item</th>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>",
        unsafe_allow_html=True)
    if open_:
        st.caption("Prices are per unit as quoted, before any conversion. Green is clear, amber needs review, purple means several options, "
                   "grey is missing or excluded. Totals are the quoted lines at your RFQ quantities, before tax, with the lowest option counted.")


def _terms(quote: Quotation) -> str:
    parts = [p for p in (
        quote.quote_reference, quote.quote_date_text,
        (quote.validity_text if quote.validity_text.lower().startswith("valid") else f"valid {quote.validity_text}") if quote.validity_text else None,
        f"payment: {quote.payment_terms}" if quote.payment_terms else None, quote.currency,
        {"inclusive": "prices include tax", "exclusive": "prices exclude tax"}.get(quote.tax_basis)) if p]
    charges = [f"{c.kind}: {c.text}" for c in quote.charges if c.kind in ("freight", "discount") and c.scope == "quote"]
    return " · ".join(html.escape(p) for p in parts + charges)


def _keep_open(store, quote_id: str) -> None:
    """The vendor's section changes its title when its count changes, which would fold it; keep it open."""
    store.setdefault("open_vendors", set()).add(quote_id)


def _on_accept(store, rfq: RFQ, quote_id: str, scope_id: str, code: str) -> None:
    _keep_open(store, quote_id)
    quote_service.accept(store, rfq, quote_id, scope_id, code)


def _on_accept_all(store, rfq: RFQ, quote_id: str) -> None:
    _keep_open(store, quote_id)
    quote_service.accept_all(store, rfq, quote_id)


def _on_exclude(store, rfq: RFQ, quote_id: str, line_id: str, value: bool) -> None:
    _keep_open(store, quote_id)
    quote_service.set_line_excluded(store, rfq, quote_id, line_id, value)


def _on_exclude_quote(store, rfq: RFQ, quote_id: str, value: bool) -> None:
    _keep_open(store, quote_id)
    quote_service.set_quote_excluded(store, rfq, quote_id, value)


def _entries(store, rfq: RFQ, quote: Quotation) -> None:
    if not quote.review_log:
        st.markdown("<span class='chip chip-reviewed'>Ready</span> Nothing needs your attention.", unsafe_allow_html=True)
        return
    acceptable = [e for e in quote.review_log if e.status == "open" and e.code in qv.ACCEPTABLE]
    if len(acceptable) > 1:
        _, bulk = st.columns([6, 1.6])
        bulk.button(f"Accept all ({len(acceptable)})", key=f"acc-all-{quote.quotation_id}", type="primary",
                    on_click=_on_accept_all, args=(store, rfq, quote.quotation_id), use_container_width=True)
    shown_options: set[str] = set()
    for entry in quote.review_log:
        if entry.code == "M4":  # one line per option group; the lines below carry the Exclude buttons
            if entry.message in shown_options:
                continue
            shown_options.add(entry.message)
        text, action = st.columns([6, 1.6], vertical_alignment="center")
        kind = {"reviewed": "reviewed", "fixed": "fixed"}.get(entry.status, "fix" if entry.blocking else "review")
        label = {"reviewed": "Reviewed", "fixed": "Fixed", "fix": "Fix", "review": "Review"}[kind]
        text.markdown(f"<span class='chip chip-{kind}'>{label}</span> {html.escape(entry.message)}", unsafe_allow_html=True)
        if entry.status != "open" or entry.code == "M4":
            continue
        key = f"{quote.quotation_id}-{entry.key}"
        if entry.code in qv.ACCEPTABLE:
            action.button("Accept", key=f"acc-{key}", on_click=_on_accept, args=(store, rfq, quote.quotation_id, entry.scope_id, entry.code),
                          use_container_width=True)
        elif entry.scope_id == quote.quotation_id:
            action.button("Exclude file", key=f"exq-{key}", on_click=_on_exclude_quote, args=(store, rfq, quote.quotation_id, True),
                          use_container_width=True)
        else:
            action.button("Exclude line", key=f"exl-{key}", on_click=_on_exclude, args=(store, rfq, quote.quotation_id, entry.scope_id, True),
                          use_container_width=True)


def _line_row(store, rfq: RFQ, quote: Quotation, line: QuotedLineItem, items: dict[str, RequestedItem]) -> None:
    item = items.get(line.matched_rfq_item_id or "")
    state = "excluded" if line.excluded else "review" if any(f.open for f in line.flags) else "ok"
    with st.container(key=f"row-{'review' if state == 'review' else 'ok'}-{quote.quotation_id}-{line.line_id}"):
        what, qty, price, status, action, evidence = st.columns(COLUMNS, vertical_alignment="center")
        what.markdown(f"**{html.escape(line.source_description)}**" + (f"  ↔  {html.escape(item.catalogue_title or item.original_text)}" if item else "  ·  not on your RFQ"))
        qty.write(f"{line.quantity:g} {line.unit_text or ''}".strip() if line.quantity is not None else "no quantity")
        price.write(price_label(line))
        chip = {"matched": ":green-badge[Matched]", "possible": ":blue-badge[Possible]", "no_match": ":gray-badge[Not on RFQ]", "extra": ":gray-badge[Extra]"}[line.match_status]
        status.markdown(":gray-badge[Excluded]" if line.excluded else chip)
        action.button("Include" if line.excluded else "Exclude", key=f"lx-{quote.quotation_id}-{line.line_id}", on_click=_on_exclude,
                      args=(store, rfq, quote.quotation_id, line.line_id, not line.excluded), use_container_width=True)
        with evidence.popover("Source", use_container_width=True):
            st.caption(f"{quote.source_filename} · {line.row_ref}")
            st.write(line.source_quote or "(no source text)")


def _vendor(store, rfq: RFQ, quote: Quotation) -> None:
    open_n = len(qv.open_flags(quote))
    badge = ":gray-badge[Excluded]" if quote.excluded else (f":orange-badge[{open_n} to review]" if open_n else ":green-badge[Ready]")
    label = f"**{quote.display_name}**   {covered(quote, rfq)}/{len(rfq.items)} quoted · {total_label(quote, rfq)}   {badge}"
    with st.expander(label, expanded=quote.quotation_id in store.get("open_vendors", set())):
        st.markdown(f"<div class='terms'>{_terms(quote)}</div>", unsafe_allow_html=True)
        if quote.excluded:
            st.button("Include this quotation again", key=f"inq-{quote.quotation_id}", on_click=_on_exclude_quote,
                      args=(store, rfq, quote.quotation_id, False))
            return
        _entries(store, rfq, quote)
        st.divider()
        items = {i.item_id: i for i in rfq.items}
        head = st.columns(COLUMNS)
        for col, label in zip(head, ["Vendor line  ↔  your RFQ item", "Quantity", "Price", "Match", "", ""]):
            col.markdown(f"<span class='th'>{label}</span>", unsafe_allow_html=True)
        for line in quote.lines:
            _line_row(store, rfq, quote, line, items)
        st.button("Exclude this quotation", key=f"exq-all-{quote.quotation_id}", on_click=_on_exclude_quote,
                  args=(store, rfq, quote.quotation_id, True))


def render(store: MutableMapping[str, Any], rfq: RFQ) -> None:
    quotes = usable(store)
    shown = [q for q in quotes if not q.excluded]
    if not quotes:
        st.info("Upload and analyse at least one quotation to review it here.")
        return
    _tiles(store, rfq, shown or quotes)
    if shown:
        _matrix(store, rfq, shown)
    st.markdown("#### Vendor-wise Quote Review")
    for quote in quotes:
        _vendor(store, rfq, quote)
