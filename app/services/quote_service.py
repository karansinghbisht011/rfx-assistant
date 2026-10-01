"""Quotation workflow: validate, parse, extract (G3), match (code + G4), verify, and the buyer's actions.

Files can be read one at a time (`process_file`) or two at a time (`run_files`). In the parallel path only
the network call to Gemini runs in a worker thread; everything that touches the session (state, counters,
results) stays in the calling thread, which receives progress as events.
"""

import queue
import threading
import time
from collections.abc import Callable, Iterator, MutableMapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from app import config, state
from app.schemas.llm import WireExtractedQuote
from app.schemas.quotation import Quotation
from app.schemas.rfq import RFQ
from app.services import quote_extraction, quote_matching, quote_verifiers
from app.services.document_ingestion import IngestionError, ParsedDocument, parse_document, validate_upload
from app.services.gemini_client import GeminiClient, GeminiError, NotConfigured, RateLimited

STAGES = ("read", "extract", "match", "check")   # progress milestones reported per file


def _set_status(quote: Quotation, new: str) -> None:
    state.check_transition("quotation", quote.status, new)
    quote.status = new  # type: ignore[assignment]


def _reject(quote: Quotation, reason: str) -> Quotation:
    quote.reject_reason = reason
    if quote.status != "rejected":
        _set_status(quote, "rejected")
    return quote


def _fail(quote: Quotation, reason: str) -> Quotation:
    """A problem that may pass on retry (rate limit, call cap): the file is kept so it can be tried again."""
    quote.reject_reason = reason
    if quote.status in ("uploaded", "parsed"):
        _set_status(quote, "failed")
    return quote


def _explain(quote: Quotation, exc: BaseException) -> Quotation:
    """Turn an error from reading a file into a status the buyer can act on."""
    if isinstance(exc, state.CallLimitReached):
        return _fail(quote, "The AI call limit for this session has been reached.")
    if isinstance(exc, RateLimited):
        return _fail(quote, "The AI service is busy (rate limit). Try this file again in a minute.")
    if isinstance(exc, NotConfigured):
        return _fail(quote, str(exc))
    return _fail(quote, "This file could not be read. Try it again.")


def quotes_of(store: MutableMapping[str, Any]) -> list[Quotation]:
    return list(store["quotations"].values())


def _prepare(store: MutableMapping[str, Any], quote: Quotation, filename: str, data: bytes) -> ParsedDocument | None:
    """Validate and parse a file. A file that cannot be used is rejected here, before any AI call."""
    store.setdefault("quote_files", {})[quote.quotation_id] = (filename, data)
    seen = {q.file_hash for q in store["quotations"].values()
            if q.file_hash and q.quotation_id != quote.quotation_id and q.status != "rejected"}
    try:
        quote.file_hash = validate_upload(filename, data, seen)
        doc = parse_document(filename, data)
    except IngestionError as exc:
        _reject(quote, str(exc))
        return None
    if quote.status in ("failed", "uploaded"):
        _set_status(quote, "parsed")
    quote.source_rows = doc.row_map()
    quote.read_from_image, quote.hidden_sheets = doc.read_from_image, doc.hidden_sheets
    quote.uncached_formulas, quote.table_row_count = doc.uncached_formulas, doc.tabular_rows
    return doc


def _apply(quote: Quotation, wire: WireExtractedQuote, doc: ParsedDocument) -> bool:
    """Build the quotation from the extraction; False when the file holds no quotation."""
    if not wire.is_quotation or not wire.lines:
        _reject(quote, "No quotation was found in this file (no priced items).")
        return False
    quote_extraction.apply_extraction(quote, wire, doc.as_text())
    return True


def _match(store: MutableMapping[str, Any], quote: Quotation, rfq: RFQ, client: GeminiClient) -> None:
    try:
        quote_matching.match_quote(client, store, quote, rfq)
    except (state.CallLimitReached, GeminiError):
        quote.notes.append("Some lines could not be matched automatically.")


def _check(store: MutableMapping[str, Any], rfq: RFQ) -> None:
    quote_verifiers.refresh_all(quotes_of(store), rfq)


def process_file(store: MutableMapping[str, Any], filename: str, data: bytes, rfq: RFQ, client: GeminiClient,
                 progress: Callable[[str, Quotation], None] | None = None, quote: Quotation | None = None) -> Quotation:
    """Run one file through the whole pipeline. Never raises: problems become a rejected or failed quotation."""
    if quote is None:
        quote = Quotation(source_filename=filename)
        store["quotations"][quote.quotation_id] = quote

    def report(stage: str) -> None:
        if progress:
            progress(stage, quote)

    report("read")
    doc = _prepare(store, quote, filename, data)
    if doc is None:
        return quote
    report("extract")
    try:
        wire = quote_extraction.extract(client, doc, data if doc.read_from_image else None,
                                        lambda: state.record_gemini_call(store))
    except Exception as exc:
        return _explain(quote, exc)
    if not _apply(quote, wire, doc):
        return quote
    report("match")
    _match(store, quote, rfq, client)
    report("check")
    _check(store, rfq)
    return quote


def process_files(store: MutableMapping[str, Any], files: list[tuple[str, bytes]], rfq: RFQ, client: GeminiClient,
                  progress: Callable[[str, Quotation], None] | None = None) -> list[Quotation]:
    """Files one after another, with a short pause so a free-tier rate limit is not hit."""
    out = []
    for n, (name, data) in enumerate(files):
        if n:
            time.sleep(config.QUOTE_CALL_SPACING_SECONDS)
        out.append(process_file(store, name, data, rfq, client, progress))
    return out


# ---------------------------------------------------------------- reading several files at once
@dataclass
class Event:
    kind: str                       # stage, line, done or tick
    index: int = -1                 # which file (position in the list given to run_files)
    stage: str | None = None
    line: dict | None = None        # a finished line as the model wrote it (live preview)
    quote: Quotation | None = None


class CallBudget:
    """Thread-safe counter that stops further AI calls once the session cap would be passed."""

    def __init__(self, limit: int):
        self.limit, self.used, self._lock = limit, 0, threading.Lock()

    def take(self) -> None:
        with self._lock:
            if self.used >= self.limit:
                raise state.CallLimitReached(f"Session limit of {config.MAX_CALLS_PER_SESSION} AI calls reached")
            self.used += 1


def run_files(store: MutableMapping[str, Any], files: list[tuple[str, bytes]], rfq: RFQ, client: GeminiClient,
              existing: list[Quotation | None] | None = None, workers: int | None = None) -> Iterator[Event]:
    """Read files `workers` at a time and report progress as events. The caller draws them.

    Workers only run the Gemini read and push events to a queue; validation, matching, verifiers and all
    session writes happen in the calling thread. A rate limit in one file fails only that file.
    """
    inbox: queue.Queue = queue.Queue()
    jobs: dict[int, tuple[Quotation, ParsedDocument, bytes]] = {}
    for i, (name, data) in enumerate(files):
        quote = (existing[i] if existing and existing[i] is not None else None) or Quotation(source_filename=name)
        store["quotations"][quote.quotation_id] = quote
        yield Event("stage", i, "read")
        doc = _prepare(store, quote, name, data)
        if doc is None:
            yield Event("done", i, quote=quote)
        else:
            jobs[i] = (quote, doc, data)
    if not jobs:
        return

    budget = CallBudget(max(config.MAX_CALLS_PER_SESSION - store["gemini_calls"], 0))

    def work(i: int) -> None:
        quote, doc, data = jobs[i]
        inbox.put(("stage", i, "extract", None))
        try:
            wire = quote_extraction.extract(client, doc, data if doc.read_from_image else None, budget.take,
                                            on_line=lambda line: inbox.put(("line", i, line, None)))
            inbox.put(("extracted", i, wire, None))
        except BaseException as exc:  # reported to the caller; a failing worker never stops the others
            inbox.put(("extracted", i, None, exc))

    pending = set(jobs)
    pool = ThreadPoolExecutor(max_workers=workers or config.QUOTE_CONCURRENCY)
    try:
        for i in jobs:
            pool.submit(work, i)
        while pending:
            try:
                kind, i, payload, error = inbox.get(timeout=0.4)
            except queue.Empty:
                yield Event("tick")
                continue
            if kind == "stage":
                yield Event("stage", i, payload)
            elif kind == "line":
                yield Event("line", i, line=payload)
            else:
                quote, doc, _ = jobs[i]
                pending.discard(i)
                if error is not None:
                    _explain(quote, error)
                elif _apply(quote, payload, doc):
                    yield Event("stage", i, "match")
                    _match(store, quote, rfq, client)
                    yield Event("stage", i, "check")
                    _check(store, rfq)
                yield Event("done", i, quote=quote)
    finally:
        pool.shutdown(wait=True)
        store["gemini_calls"] += budget.used


def retry(store: MutableMapping[str, Any], quote_id: str, rfq: RFQ, client: GeminiClient,
          progress: Callable[[str, Quotation], None] | None = None) -> Quotation:
    quote = store["quotations"][quote_id]
    name, data = store["quote_files"][quote_id]
    quote.reject_reason = None
    return process_file(store, name, data, rfq, client, progress, quote=quote)


def remove(store: MutableMapping[str, Any], quote_id: str) -> None:
    store["quotations"].pop(quote_id, None)
    store.get("quote_files", {}).pop(quote_id, None)


def accept(store: MutableMapping[str, Any], rfq: RFQ, quote_id: str, scope_id: str, code: str) -> None:
    """The buyer accepts a flag as it is (only flags that can be accepted)."""
    quote = store["quotations"][quote_id]
    if code not in quote_verifiers.ACCEPTABLE:
        return
    target = quote.acknowledged if scope_id == quote.quotation_id else next(
        (l.acknowledged for l in quote.lines if l.line_id == scope_id), None)
    if target is not None and code not in target:
        target.append(code)
    quote_verifiers.refresh_all(quotes_of(store), rfq)


def accept_all(store: MutableMapping[str, Any], rfq: RFQ, quote_id: str) -> None:
    """Accept every open flag of one quotation that the buyer is allowed to accept."""
    quote = store["quotations"][quote_id]
    lines = {l.line_id: l for l in quote.lines}
    for entry in quote.review_log:
        if entry.status != "open" or entry.code not in quote_verifiers.ACCEPTABLE:
            continue
        target = quote.acknowledged if entry.scope_id == quote.quotation_id else (
            lines[entry.scope_id].acknowledged if entry.scope_id in lines else None)
        if target is not None and entry.code not in target:
            target.append(entry.code)
    quote_verifiers.refresh_all(quotes_of(store), rfq)


def set_line_excluded(store: MutableMapping[str, Any], rfq: RFQ, quote_id: str, line_id: str, excluded: bool) -> None:
    quote = store["quotations"][quote_id]
    for line in quote.lines:
        if line.line_id == line_id:
            line.excluded = excluded
    quote_verifiers.refresh_all(quotes_of(store), rfq)


def set_quote_excluded(store: MutableMapping[str, Any], rfq: RFQ, quote_id: str, excluded: bool) -> None:
    store["quotations"][quote_id].excluded = excluded
    quote_verifiers.refresh_all(quotes_of(store), rfq)
