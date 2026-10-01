"""The Purchase Proposal card and the section headings used on the Compare page."""

import html
from decimal import Decimal

import streamlit as st

from app.schemas.analyst import AnalystTurn, Proposal

SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}
DOTS = ["#0E7C7B", "#E9A23B", "#5B2F91", "#1D4577", "#B42318", "#17803D", "#8A5A00", "#2F6F9F"]


def fmt(amount: Decimal | None, currency: str = "INR", places: int = 2) -> str:
    if amount is None:
        return "—"
    return f"{SYMBOLS.get(currency, currency + ' ')}{amount:,.{places}f}"


def qty(value: Decimal) -> str:
    return f"{value:,.0f}" if value == value.to_integral_value() else f"{value:g}"


def dot(vendor: str, order: list[str]) -> str:
    colour = DOTS[order.index(vendor) % len(DOTS)] if vendor in order else DOTS[0]
    return f"<span class='vdot' style='background:{colour}'></span>"


def heading(title: str, sub: str = "") -> None:
    st.markdown(f"<div class='sec-h'><span class='sec-bar'></span><div><div class='sec-t'>{html.escape(title)}</div>"
                + (f"<div class='sec-s'>{html.escape(sub)}</div>" if sub else "") + "</div></div>", unsafe_allow_html=True)


def _delta(proposal: Proposal) -> str:
    chips = []
    cur = proposal.currency
    if proposal.grand_total is not None and proposal.cheapest_possible_total is not None:
        gap = proposal.grand_total - proposal.cheapest_possible_total
        if gap > 0:
            chips.append(f"<span class='pp-chip pp-warn'>{fmt(gap, cur)} above the cheapest possible, the cost of your rules</span>")
        else:
            chips.append("<span class='pp-chip pp-good'>As low as the offers allow</span>")
    if proposal.grand_total is not None and proposal.best_single:
        label, total = proposal.best_single
        diff = total - proposal.grand_total
        if diff > 0:
            chips.append(f"<span class='pp-chip pp-good'>{fmt(diff, cur)} below the best single vendor ({html.escape(label)})</span>")
        elif diff < 0:
            chips.append(f"<span class='pp-chip pp-warn'>{fmt(-diff, cur)} above the best single vendor ({html.escape(label)})</span>")
        else:
            chips.append(f"<span class='pp-chip'>Same as the best single vendor ({html.escape(label)})</span>")
    return "".join(chips)


def _rules(proposal: Proposal) -> str:
    return "".join(
        f"<span class='pp-rule {'pp-met' if r.met else 'pp-unmet'}' title='{html.escape(r.detail)}'>{'✓' if r.met else '!'} {html.escape(r.text)}"
        + (f"<small>{html.escape(r.detail)}</small>" if r.detail else "") + "</span>"
        for r in proposal.rules)


def _table(proposal: Proposal, vendors: list[str]) -> str:
    cur = proposal.currency
    body, seen = [], set()
    counts: dict[str, int] = {}
    for r in proposal.rows:
        counts[r.item_id] = counts.get(r.item_id, 0) + 1
    for r in proposal.rows:
        first = r.item_id not in seen
        seen.add(r.item_id)
        split = "<span class='pp-split'>split</span>" if counts[r.item_id] > 1 and first else ""
        item = f"<b>{html.escape(r.item)}</b>{split}" if first else ""
        need = f"{qty(r.required_qty)} {html.escape(r.unit)}" if first else ""
        quoted = f"<small>quoted {html.escape(r.quoted_price)} {html.escape(r.quoted_currency)}</small>" if r.quoted_price and r.quoted_currency and r.quoted_currency != cur else ""
        body.append(
            f"<tr class='{'pp-first' if first else ''}'><td class='pp-item'>{item}</td><td>{need}</td>"
            f"<td>{dot(r.vendor, vendors)}{html.escape(r.vendor)}</td><td class='pp-num'>{qty(r.quantity)} {html.escape(r.unit)}</td>"
            f"<td class='pp-num'>{fmt(r.unit_price, cur)}{quoted}</td><td class='pp-num'><b>{fmt(r.total, cur)}</b></td></tr>")
    for name in proposal.unfilled:
        body.append(f"<tr class='pp-first'><td class='pp-item'><b>{html.escape(name)}</b></td><td colspan='5'>"
                    "<span class='mx mx-missing'>not priced by any vendor</span></td></tr>")
    body.append(f"<tr class='pp-sum'><td colspan='5'>Grand total <small>before tax, {html.escape(cur)}</small></td>"
                f"<td class='pp-num'>{fmt(proposal.grand_total, cur)}</td></tr>")
    head = ("<th>Item</th><th>Required</th><th>Vendor</th><th class='pp-num'>Quantity</th>"
            "<th class='pp-num'>Unit price</th><th class='pp-num'>Total</th>")
    return f"<div class='matrix-wrap'><table class='pp-table'><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"


def proposal_card(turn: AnalystTurn, vendors: list[str], latest: bool = True) -> None:
    p = turn.proposal
    if p is None:
        return
    vendors_used = len({r.vendor for r in p.rows})
    st.markdown(
        "<div class='pp-card'>"
        f"<div class='pp-top'><div><div class='pp-label'>{'Purchase Proposal' if latest else 'Earlier proposal'}</div>"
        f"<div class='pp-total'>{fmt(p.grand_total, p.currency)}</div>"
        f"<div class='pp-sub'>{len(p.rows)} line{'s' if len(p.rows) != 1 else ''} from {vendors_used} vendor{'s' if vendors_used != 1 else ''}</div></div>"
        f"<div class='pp-ask'>“{html.escape(turn.question[:160])}”</div></div>"
        f"<div class='pp-chips'>{_delta(p)}</div><div class='pp-rules'>{_rules(p)}</div></div>",
        unsafe_allow_html=True)
    if p.rows:
        st.markdown(_table(p, vendors), unsafe_allow_html=True)
    if p.caveats:
        with st.expander("Assumptions and notes", expanded=False):
            for c in p.caveats:
                st.markdown(f"- {c}")


def empty_card() -> None:
    st.markdown(
        "<div class='pp-card pp-empty'><div class='pp-label'>Purchase Proposal</div>"
        "<div class='pp-empty-t'>Ask the analyst for a purchase proposal</div>"
        "<div class='pp-sub'>Describe what you want in the chat on the right. For example, allow the same item to be split between vendors, "
        "or make sure every vendor that responded gets part of the order. The proposal appears here, calculated from your quotations.</div></div>",
        unsafe_allow_html=True)
