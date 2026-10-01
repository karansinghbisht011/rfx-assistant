"""Catalogue picker: a wide popover with suggested close matches and a search box."""

import streamlit as st

from app.schemas.rfq import RequestedItem
from app.services import rfq_service
from app.ui import resources


def render(col, item: RequestedItem, on_pick) -> None:
    unresolved = item.catalogue_title is None
    with col.popover("Choose item" if unresolved else "Change item", use_container_width=True):
        st.markdown("**Find the right catalogue item**")
        query = st.text_input(
            "Search the catalogue",
            key=f"search-{item.item_id}",
            placeholder="Search 13,000+ catalogue items…",
            label_visibility="collapsed",
        )
        if item.catalogue_title:
            st.markdown(f"<div class='pick-meta'>Current item: <b>{item.catalogue_title}</b></div>", unsafe_allow_html=True)
        phrase = rfq_service.search_phrase(item)
        if len(query.strip()) >= 2:
            options, heading = resources.suggestions(query.strip(), 8), f"Results for “{query.strip()}”"
        else:
            options = item.match_candidates or resources.suggestions(phrase, 6)
            heading = f"Suggested matches for “{phrase}”"
        st.caption(f"{heading}  ·  press Enter after typing to search")
        options = [c for c in options if c.code != item.catalogue_code]
        if not options:
            st.caption("No other close matches. Try different words.")
        for candidate in options:
            st.button(
                candidate.title,
                key=f"pick-{item.item_id}-{candidate.code}",
                on_click=on_pick,
                args=(item.item_id, candidate),
                use_container_width=True,
            )
            st.markdown(
                f"<div class='pick-meta'>{candidate.class_title} · default unit {candidate.default_unit}"
                f" · {candidate.score:.0f}% match</div>",
                unsafe_allow_html=True,
            )
