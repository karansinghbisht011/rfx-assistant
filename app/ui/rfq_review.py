"""Review summary (right panel): every flagged line stays listed and changes state as the buyer works.

open (Fix / Review)  ->  Reviewed (accepted, green)  or  Fixed (edited below, mint green).
"""

import html

import streamlit as st

from app.schemas.flags import ReviewEntry
from app.schemas.rfq import RFQ
from app.services import verifiers
from app.ui import rfq_actions as actions


def _chip(entry: ReviewEntry) -> str:
    if entry.status == "reviewed":
        kind, label = "reviewed", "Reviewed"
    elif entry.status == "fixed":
        kind, label = "fixed", "Fixed"
    elif entry.blocking:
        kind, label = "fix", "Fix"
    else:
        kind, label = "review", "Review"
    return f"<span class='chip chip-{kind}'>{label}</span>"


def render(rfq: RFQ) -> None:
    log = rfq.review_log
    if not log:
        with st.container(border=True, key="card-clear"):
            st.markdown("**All clear** :green-badge[Ready]")
            st.write("Every line is confirmed. Review the table, then save your RFQ.")
        return

    open_entries = [e for e in log if e.status == "open"]
    done = len(log) - len(open_entries)
    with st.container(border=True, key="card-review-summary" if open_entries else "card-clear"):
        if open_entries:
            st.markdown(f"**Review summary** :orange-badge[{len(open_entries)} to review]")
            fixes = sum(1 for e in open_entries if e.blocking)
            st.caption(
                f"{fixes} need a quantity or unit in the table below." if fixes
                else "Accept what is fine as it is, or change it in the table."
            )
        else:
            st.markdown("**Review summary** :green-badge[All clear]")
            st.caption("Everything has been reviewed or fixed. Check the table, then save your RFQ.")
        with st.container(height=330, border=False):
            for entry in log:
                text, action = st.columns([6, 1.2], vertical_alignment="center")
                text.markdown(f"{_chip(entry)} {html.escape(entry.message)}", unsafe_allow_html=True)
                if entry.status == "open" and entry.code in verifiers.ACCEPTABLE_CODES:
                    action.button(
                        "Accept",
                        key=f"accept-{entry.scope_id}-{entry.code}",
                        on_click=actions.on_accept,
                        args=(rfq, entry.scope_id, entry.code),
                        use_container_width=True,
                    )
        if done and open_entries:
            st.caption(f"{done} done")
