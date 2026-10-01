"""Compare step: the lowest offers, single-vendor totals and an indicative combination, all calculated by code."""

import html
from collections.abc import MutableMapping
from decimal import Decimal, InvalidOperation
from typing import Any

import streamlit as st

from app import config
from app.schemas.analysis import Assumptions
from app.schemas.rfq import RFQ
from app.services import comparison, fx
from app.ui import analyst_panel, proposal_view
from app.ui import evaluate_review as review

CODE_LABELS = {
    "excluded": "Excluded by you", "unmatched": "Not one of your RFQ items", "unpriced": "No price",
    "flagged": "Open review point", "unit": "Unit cannot be compared", "tax": "Tax rate not stated",
    "currency": "Currency not stated", "option": "A lower option from the same vendor is used",
}


def _currencies(quotes) -> set[str]:
    return {(l.currency or q.currency) for q in quotes for l in q.lines if (l.currency or q.currency)} - {config.COMPARISON_CURRENCY}


def _rates(store: MutableMapping[str, Any], quotes) -> dict[str, fx.FxRate]:
    """Rates for the currencies in use. Looked up once per currency per session; the buyer can refresh or override."""
    rates: dict[str, fx.FxRate] = store.setdefault("fx_rates", {})
    tried: set[str] = store.setdefault("fx_tried", set())
    wanted = {c for c in _currencies(quotes) if c not in rates and c not in tried}
    if wanted:
        tried |= wanted
        rates.update(fx.fetch_rates(wanted))
    return rates


def _refresh_rates(store) -> None:
    store["fx_tried"] = set()
    store["fx_rates"] = {c: r for c, r in store.get("fx_rates", {}).items() if r.manual}


def _on_rate(store, currency: str) -> None:
    raw = str(st.session_state.get(f"cmp-rate-{currency}") or "").strip()
    overrides = dict(store.setdefault("fx_override", {}))
    try:
        value = Decimal(raw) if raw else None
    except InvalidOperation:
        value = None
    if value is not None and fx.valid_rate(value):
        overrides[currency] = value
    else:
        overrides.pop(currency, None)
    store["fx_override"] = overrides


def _rates_panel(store, quotes, rates: dict[str, fx.FxRate]) -> None:
    currencies = sorted(_currencies(quotes))
    if not currencies:
        return
    override = store.get("fx_override", {})
    with st.expander(f"Exchange rates to {config.COMPARISON_CURRENCY}", expanded=any(c not in rates and c not in override for c in currencies)):
        for currency in currencies:
            used = override.get(currency)
            looked_up = rates.get(currency)
            c1, c2 = st.columns([3, 2], vertical_alignment="center")
            if used:
                c1.markdown(f"**1 {currency} = {used:g} {config.COMPARISON_CURRENCY}** · entered by you")
            elif looked_up:
                c1.markdown(f"**1 {currency} = {looked_up.rate:g} {config.COMPARISON_CURRENCY}** · {looked_up.source}, {looked_up.as_of}")
            else:
                c1.markdown(f"**{currency}**: no rate available. Enter one to include these prices.")
            c2.text_input(f"Rate for {currency}", value=f"{used:g}" if used else "", placeholder=f"1 {currency} in {config.COMPARISON_CURRENCY}",
                          key=f"cmp-rate-{currency}", on_change=_on_rate, args=(store, currency), label_visibility="collapsed")
        st.button("Look up rates again", key="cmp-refresh", on_click=_refresh_rates, args=(store,))


def _price(o: comparison.Offer) -> str:
    symbol = review.SYMBOLS.get(o.currency, f"{o.currency} ")
    return f"{symbol}{o.unit_price:,.2f}"


def _table(analysis: comparison.Analysis, rfq: RFQ) -> None:
    base = analysis.base_currency
    rows = []
    for item in rfq.items:
        low = analysis.lowest.get(item.item_id)
        qty = f"{item.quantity:g} {item.unit}" if item.quantity is not None else ""
        name = f"{html.escape(item.catalogue_title or item.original_text)}<small>{qty}</small>"
        if not low:
            reason = "no comparable offer"
            rows.append(f"<tr><td class='item'>{name}</td><td colspan='4'><span class='mx mx-missing'>{reason}</span></td></tr>")
            continue
        o = low[0]
        others = len([x for x in analysis.offers if x.item_id == item.item_id and x.cost_base is not None]) - len(low)
        who = " / ".join(html.escape(x.vendor) for x in low) + (" <span class='mx mx-possible'>tie</span>" if len(low) > 1 else "")
        flag = " <span class='mx mx-review'>under review</span>" if o.flagged else ""
        rows.append(f"<tr><td class='item'>{name}</td><td>{who}{flag}</td><td>{_price(o)}</td>"
                    f"<td><b>{review.money(o.cost_base, base)}</b></td><td>{others} other{'s' if others != 1 else ''}</td></tr>")
    total = sum((low[0].cost_base for low in analysis.lowest.values()), Decimal(0))
    partial = len(analysis.lowest) < len(rfq.items)
    label = f"Total of the lowest offers{' (partial: some items have no comparable offer)' if partial else ''}"
    rows.append(f"<tr class='pp-sum'><td colspan='3'>{label} <small>before tax, {html.escape(base)}</small></td>"
                f"<td colspan='2'><b>{review.money(total, base)}</b></td></tr>")
    head = "<th>RFQ item</th><th>Lowest offer</th><th>Unit price (quoted)</th><th>Cost at RFQ quantity</th><th>Compared with</th>"
    st.markdown(f"<div class='matrix-wrap'><table class='matrix'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>",
                unsafe_allow_html=True)
    st.caption(f"Costs are the unit price × your quantity, before tax, in {base}. Tax-inclusive prices have the stated tax taken out.")


def _singles(analysis: comparison.Analysis, rfq: RFQ) -> None:
    base = analysis.base_currency
    names = {i.item_id: i.catalogue_title or i.original_text for i in rfq.items}
    rows = []
    for s in analysis.singles:
        status = (f"<span class='mx mx-ok'>covers all {len(rfq.items)} items</span>" if s.complete
                  else f"<span class='mx mx-missing'>missing {len(s.missing_item_ids)}: {html.escape(', '.join(names[i] for i in s.missing_item_ids[:3]))}"
                       f"{'…' if len(s.missing_item_ids) > 3 else ''}</span>")
        total = review.money(s.total, base) if s.total is not None else "none"
        cell = f"<b>{total}</b>" if s.complete else (f"<span class='mx mx-missing'>partial {total}</span>" if s.total is not None else "—")
        rows.append(f"<tr><td class='item'>{html.escape(s.label)}</td><td>{status}</td><td>{cell}</td></tr>")
    st.markdown("<div class='matrix-wrap'><table class='matrix'><thead><tr><th>Vendor</th><th>Coverage</th><th>Total for all items</th></tr></thead>"
                f"<tbody>{''.join(rows)}</tbody></table></div>", unsafe_allow_html=True)


def _left_out(analysis: comparison.Analysis) -> None:
    if not analysis.exclusions and not analysis.notes:
        return
    with st.expander(f"Left out of the comparison ({len(analysis.exclusions)})", expanded=False):
        for note in analysis.notes:
            st.markdown(f"- {note}")
        groups: dict[str, list[comparison.Exclusion]] = {}
        for e in analysis.exclusions:
            groups.setdefault(e.code, []).append(e)
        for code, items in groups.items():
            st.markdown(f"**{CODE_LABELS.get(code, code)}** · {len(items)}")
            for e in items[:12]:
                st.caption(f"{e.vendor}: {e.message}")
            if len(items) > 12:
                st.caption(f"…and {len(items) - 12} more")


def render(store: MutableMapping[str, Any], rfq: RFQ) -> None:
    quotes = review.usable(store)
    kept = [q for q in quotes if not q.excluded]
    if not kept:
        st.info("Keep at least one quotation in Review to compare.")
        return
    looked_up = _rates(store, kept)
    rates = {c: r.rate for c, r in looked_up.items()} | store.get("fx_override", {})
    analysis = comparison.analyse(rfq, kept, Assumptions(), rates)
    main, side = st.columns([1.75, 1], gap="large")
    with side:
        analyst_panel.render(store, rfq, kept, rates)
    vendors = sorted(analysis.vendors.values())
    with main:
        proposal_view.heading("Purchase Proposal", "Built by the analyst from your request, calculated from the quotations")
        done = [t for t in analyst_panel.turns(store) if t.proposal is not None]
        if done:
            proposal_view.proposal_card(done[-1], vendors)
            if len(done) > 1:
                with st.expander(f"Earlier proposals ({len(done) - 1})", expanded=False):
                    for t in reversed(done[:-1]):
                        proposal_view.proposal_card(t, vendors, latest=False)
        else:
            proposal_view.empty_card()
        proposal_view.heading("Lowest offer for each item", "The cheapest single vendor for each item, before tax")
        _table(analysis, rfq)
        proposal_view.heading("Vendor totals", "What each vendor's quotation comes to for the whole RFQ")
        _singles(analysis, rfq)
        _left_out(analysis)
        _rates_panel(store, kept, looked_up)
