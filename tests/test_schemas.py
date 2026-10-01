from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.analysis import Assumptions
from app.schemas.flags import ReviewFlag
from app.schemas.quotation import Quotation, QuotedLineItem
from app.schemas.rfq import RFQ, RequestedItem


def test_absent_quantity_is_not_zero():
    item = RequestedItem(original_text="gate valve")
    assert item.quantity is None
    item.quantity = Decimal("0")
    assert item.quantity == 0 and item.quantity is not None


def test_quantity_is_decimal():
    item = RequestedItem(original_text="cable", quantity="20.5")
    assert item.quantity == Decimal("20.5")


def test_invalid_match_status_rejected():
    with pytest.raises(ValidationError):
        RequestedItem(original_text="x", match_status="guess")


def test_rfq_defaults():
    rfq = RFQ(name="RFQ-2026-10-01")
    assert rfq.status == "draft" and rfq.items == []
    assert rfq.rfq_id.startswith("rfq-")
    assert rfq.buyer_details.company_name


def test_missing_price_stays_missing():
    line = QuotedLineItem(row_ref="S1!R4", source_description="Pressure transmitter")
    assert line.unit_price is None
    assert Quotation(source_filename="q.xlsx").status == "uploaded"


def test_flag_open_until_resolved():
    flag = ReviewFlag(code="Q19", severity="review", scope="quote_line", scope_id="line-1", message="Unit not stated")
    assert flag.open
    flag.resolution = "accepted"
    assert not flag.open


def test_assumptions_active():
    assert not Assumptions().active()
    assert Assumptions(max_vendors=2).active()
