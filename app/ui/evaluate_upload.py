"""Upload step: add files, analyse them with a live progress screen, and manage what was read."""

import time
from collections.abc import MutableMapping
from typing import Any

import streamlit as st

from app import config
from app.schemas.quotation import Quotation
from app.schemas.rfq import RFQ
from app.services import quote_service, quote_verifiers
from app.services.document_ingestion import ALLOWED_EXTENSIONS, SUPPORTED_TEXT
from app.ui import analysis_loader, resources
from app.ui import stepper
from app.ui.components import notice


def _begin(store: MutableMapping[str, Any], files) -> None:
    store["analysing"] = [(f.name, f.getvalue()) for f in files]
    store.setdefault("seen_uploads", set()).update(f.file_id for f in files)


def _retry(store, rfq: RFQ, quote_id: str) -> None:
    store["retrying"] = quote_id


def _remove(store, quote_id: str) -> None:
    quote_service.remove(store, quote_id)


def _status_chip(q: Quotation) -> str:
    if q.status == "rejected":
        return ":red-badge[Not used]"
    if q.status == "failed":
        return ":orange-badge[Try again]"
    open_n = len(quote_verifiers.open_flags(q))
    return f":orange-badge[{open_n} to review]" if open_n else ":green-badge[Ready]"


def _summary(q: Quotation) -> str:
    if q.status in ("rejected", "failed"):
        return q.reject_reason or ""
    open_n = len(quote_verifiers.open_flags(q))
    base = f"{q.display_name} · {len(q.lines)} lines"
    return base + (f" · {open_n} to review" if open_n else "")


_OUTCOME = {"rejected": "rejected", "failed": "failed"}


def render_analysing(store: MutableMapping[str, Any], rfq: RFQ) -> None:
    """The loading screen. Files are read two at a time; each shows the lines it finds as they arrive,
    and a rate limit on one file never stops the rest."""
    files = store.pop("analysing")
    tracker = [analysis_loader.FileProgress(name) for name, _ in files]
    with st.container(border=True, key="card-analysing"):
        slot = st.empty()

    def draw() -> None:
        slot.markdown(analysis_loader.render_html(tracker, quote_service.quotes_of(store)), unsafe_allow_html=True)

    draw()
    for event in quote_service.run_files(store, files, rfq, resources.client()):
        if event.kind == "tick":
            draw()
            continue
        f = tracker[event.index]
        if event.kind == "stage":
            f.status, f.stage = "active", event.stage
            if event.stage == "extract":
                f.started = time.time()
        elif event.kind == "line":
            f.found.append(analysis_loader.feed_text(event.line or {}))
        elif event.kind == "done":
            f.status = _OUTCOME.get(event.quote.status, "done")
            f.summary = _summary(event.quote)
        draw()
    time.sleep(0.8)
    if any(q.status not in ("rejected", "failed") for q in quote_service.quotes_of(store)):
        stepper.go(store, 3)
    st.rerun()


def render_retry(store: MutableMapping[str, Any], rfq: RFQ) -> None:
    quote_id = store.pop("retrying")
    quote = store["quotations"].get(quote_id)
    if quote is None:
        st.rerun()
    tracker = [analysis_loader.FileProgress(quote.source_filename, status="active")]
    with st.container(border=True, key="card-analysing"):
        slot = st.empty()

    def draw() -> None:
        slot.markdown(analysis_loader.render_html(tracker, quote_service.quotes_of(store)), unsafe_allow_html=True)

    draw()

    def progress(stage: str, q) -> None:
        tracker[0].stage = stage
        draw()

    result = quote_service.retry(store, quote_id, rfq, resources.client(), progress)
    tracker[0].status = {"rejected": "rejected", "failed": "failed"}.get(result.status, "done")
    tracker[0].summary = _summary(result)
    draw()
    time.sleep(0.8)
    st.rerun()


def render(store: MutableMapping[str, Any], rfq: RFQ) -> None:
    st.markdown("**Upload vendor quotations**")
    st.caption(f"{SUPPORTED_TEXT}. Up to {config.MAX_FILE_MB} MB each. Each file is read on its own.")
    seen = store.setdefault("seen_uploads", set())
    uploads = st.file_uploader(
        "Vendor quotations", type=[e.lstrip(".") for e in ALLOWED_EXTENSIONS], accept_multiple_files=True,
        key=f"uploader-{store.get('uploader_gen', 0)}", label_visibility="collapsed",
    )
    new = [f for f in (uploads or []) if f.file_id not in seen]
    if st.button(f"Analyze {len(new)} quote{'s' if len(new) != 1 else ''}" if new else "Analyze quotes", type="primary", disabled=not new,
                 key="analyse"):
        _begin(store, new)
        store["uploader_gen"] = store.get("uploader_gen", 0) + 1
        st.rerun()

    quotes = quote_service.quotes_of(store)
    if not quotes:
        return
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    for q in quotes:
        with st.container(key=f"row-{'review' if q.status in ('rejected', 'failed') else 'ok'}-{q.quotation_id}"):
            name, info, action = st.columns([3, 5, 2.2], vertical_alignment="center")
            name.markdown(f"**{q.source_filename}**  {_status_chip(q)}")
            info.caption(_summary(q))
            if q.status == "failed":
                action.button("Try again", key=f"retry-{q.quotation_id}", on_click=_retry, args=(store, rfq, q.quotation_id),
                              use_container_width=True)
            else:
                action.button("Remove", key=f"rm-{q.quotation_id}", on_click=_remove, args=(store, q.quotation_id),
                              use_container_width=True)
