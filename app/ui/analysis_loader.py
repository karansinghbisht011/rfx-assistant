"""The 'Analysing your quotations' screen: live file-by-file progress with counters and stage dots."""

import html
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.schemas.quotation import Quotation
from app.services import quote_verifiers

STAGES = [("read", "Reading the file"), ("extract", "Extracting lines and terms"),
          ("match", "Matching to your RFQ"), ("check", "Running checks")]


@dataclass
class FileProgress:
    name: str
    status: str = "queued"          # queued, active, done, rejected, failed
    stage: str = "read"
    summary: str = ""
    found: list[str] = field(default_factory=list)   # lines as the model finds them (live feed)
    started: float | None = None

    @property
    def kind(self) -> str:
        return (Path(self.name).suffix.lstrip(".") or "file").upper()


FEED_SHOWN = 4


def feed_text(line: dict) -> str:
    """One streamed line as a short readable string: description, quantity and price as written."""
    desc = html.unescape(str(line.get("desc") or "").strip())[:60]
    qty = " ".join(p for p in (line.get("qty"), line.get("unit")) if p)
    price = " ".join(p for p in (line.get("cur"), line.get("price")) if p)
    return " · ".join(p for p in (desc, qty, price) if p)


def _feed(f: FileProgress) -> str:
    if not f.found:
        return ""
    recent = f.found[-FEED_SHOWN:]
    items = "".join(f"<div class='an-line'>{html.escape(t)}</div>" for t in recent)
    return f"<div class='an-feed'>{items}</div>"


def _tiles(quotes: list[Quotation]) -> str:
    usable = [q for q in quotes if q.status not in ("rejected", "failed")]
    lines = sum(len(q.lines) for q in usable)
    matched = sum(1 for q in usable for l in q.lines if l.match_status in ("matched", "possible"))
    review = sum(len(quote_verifiers.open_flags(q)) for q in usable)
    data = [("Vendors found", len(usable)), ("Lines read", lines), ("Matched to your RFQ", matched), ("To review", review)]
    return "".join(f"<div class='an-tile'><div class='an-n'>{n}</div><div class='an-l'>{label}</div></div>" for label, n in data)


def _file(f: FileProgress) -> str:
    detail = ""
    if f.status == "active":
        keys = [k for k, _ in STAGES]
        position = keys.index(f.stage)
        dots = "".join(
            f"<span class='an-st {'done' if i < position else 'active' if i == position else ''}'>{label}</span>"
            for i, (_, label) in enumerate(STAGES))
        seconds = f" · {int(time.time() - f.started)}s" if f.started else ""
        count = f"<small>{len(f.found)} line{'s' if len(f.found) != 1 else ''} found{seconds}</small>" if f.found else ""
        detail = f"<div class='an-stages'>{dots}</div>{count}{_feed(f)}"
    elif f.summary:
        detail = f"<small>{html.escape(f.summary)}</small>"
    elif f.status == "queued":
        detail = "<small>Waiting</small>"
    mark = {"done": "✓", "rejected": "✕", "failed": "!", "active": "", "queued": ""}[f.status]
    return (f"<div class='an-file an-{f.status}'><span class='an-ico'>{f.kind}</span>"
            f"<div class='an-name'><b>{html.escape(f.name)}</b>{detail}</div><span class='an-mark'>{mark}</span></div>")


def render_html(files: list[FileProgress], quotes: list[Quotation]) -> str:
    total = max(len(files), 1)
    finished = sum(1 for f in files if f.status in ("done", "rejected", "failed"))
    active = next((f for f in files if f.status == "active"), None)
    fraction = (finished + (0.5 if active else 0)) / total
    return (
        "<div class='an-head'><div class='an-title'>Analysing your quotations</div>"
        f"<div class='an-sub'>{finished} of {len(files)} files</div></div>"
        f"<div class='an-bar'><div class='an-bar-fill' style='width:{max(fraction, 0.04) * 100:.0f}%'></div></div>"
        f"<div class='an-tiles'>{_tiles(quotes)}</div>"
        f"<div class='an-files'>{''.join(_file(f) for f in files)}</div>"
    )
