"""Synthetic quotation files and a scripted Gemini for tests. These are NOT the data/test_data quotes."""

import io
from decimal import Decimal

from openpyxl import Workbook

from app.schemas.llm import WireCharge, WireExtractedLine, WireExtractedQuote, WireLineMatch, WireMatchResult
from app.schemas.rfq import RFQ, RequestedItem
from app.services.gemini_client import GeminiError, MockGemini


def make_rfq() -> RFQ:
    items = [
        RequestedItem(item_id="i-pump", original_text="2 centrifugal pumps", catalogue_title="Centrifugal pumps", quantity=Decimal(2), unit="Nos"),
        RequestedItem(item_id="i-bolt", original_text="12 hexagonal bolts", catalogue_title="Hexagonal bolts", quantity=Decimal(12), unit="Nos"),
        RequestedItem(item_id="i-valve", original_text="10 ball valves", catalogue_title="Ball valves", quantity=Decimal(10), unit="Nos"),
        RequestedItem(item_id="i-oil", original_text="3 drums pump lubricating oils", catalogue_title="Pump lubricating oils", quantity=Decimal(3), unit="Drum"),
        RequestedItem(item_id="i-ties", original_text="10 sets cable ties", catalogue_title="Cable ties", quantity=Decimal(10), unit="Set"),
    ]
    return RFQ(name="RFQ-test", items=items)


def _cell(v) -> str:
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else f"{v:.6f}".rstrip("0").rstrip(".")
    return "" if v is None else str(v)


def make_xlsx(rows: list[list], sheet: str = "Sheet1", hidden_sheet: list[list] | None = None) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    for r in rows:
        ws.append(r)
    if hidden_sheet is not None:
        hs = wb.create_sheet("Internal")
        for r in hidden_sheet:
            hs.append(r)
        hs.sheet_state = "hidden"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def row_text(cells: list) -> str:
    return " | ".join(_cell(c) for c in cells).rstrip(" |")


def wire_line(ref: str, cells: list, desc: str, qty=None, unit=None, price=None, **kw) -> WireExtractedLine:
    """A line as the model would return it: the row is its own evidence, so `src` is left out."""
    base = dict(ref=ref, desc=desc, qty=qty, unit=unit, price=price)
    base.update(kw)
    return WireExtractedLine(**base)


def wire_quote(lines: list[WireExtractedLine], **kw) -> WireExtractedQuote:
    base = dict(
        is_quotation=True, vendor="Test Vendor Pvt Ltd", quote_ref="TV/1", date="02 Oct 2026", validity="valid till 31 Dec 2099",
        payment="30 days", delivery="2 weeks", lines=lines, warnings=[],
        charges=[WireCharge(kind="tax", scope="quote", text="GST @ 18% extra")],
    )
    base.update(kw)
    return WireExtractedQuote(**base)


class ScriptedGemini(MockGemini):
    """Returns prepared answers for extraction and matching, and counts the calls."""

    def __init__(self, quote: WireExtractedQuote | None = None, matches: dict[str, tuple[str | None, str]] | None = None,
                 extract_error: Exception | None = None, match_error: Exception | None = None):
        self.quote, self.matches = quote, matches or {}
        self.extract_error, self.match_error = extract_error, match_error
        self.extract_calls = self.match_calls = 0
        self.last_match_payload: tuple[list, list] | None = None

    def extract_quote(self, document_text, pdf_bytes=None, on_line=None):
        self.extract_calls += 1
        if self.extract_error:
            raise self.extract_error
        for line in self.quote.lines if on_line else []:  # stream the lines the way the live client does
            on_line(line.model_dump(exclude_none=True))
        return self.quote

    def match_lines(self, rfq_items, lines):
        self.match_calls += 1
        self.last_match_payload = (rfq_items, lines)
        if self.match_error:
            raise self.match_error
        out = []
        for l in lines:
            item_id, status = self.matches.get(l["description"], (None, "no_match"))
            out.append(WireLineMatch(line_id=l["line_id"], rfq_item_id=item_id, status=status, differences=[], is_alternate=False, reason="test"))
        return WireMatchResult(matches=out)


def standard_rows():
    """A clean four-line quotation that follows the fake RFQ."""
    return [
        ["S.No", "Description", "Qty", "UOM", "Unit price", "Amount"],
        [1, "Centrifugal pumps", 2, "Nos", 47800, 95600],
        [2, "Hexagonal bolts", 12, "Nos", 14.5, 174],
        [3, "Ball valves", 10, "Nos", 2240, 22400],
        [4, "Pump lubricating oils", 3, "Drum", 15400, 46200],
    ]


def standard_wire(rows=None, **kw):
    rows = rows or standard_rows()
    lines = [wire_line(f"Sheet1!R{n}", r, r[1], _cell(r[2]) or None, r[3], _cell(r[4]) or None,
                       total=(_cell(r[5]) if len(r) > 5 else None) or None, cur="INR")
             for n, r in enumerate(rows[1:], start=2)]
    return wire_quote(lines, **kw)
