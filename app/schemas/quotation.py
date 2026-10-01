from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ids import new_id
from app.schemas.flags import ReviewFlag

LineMatchStatus = Literal["matched", "possible", "no_match", "extra"]
QuotationStatus = Literal["uploaded", "parsed", "needs_review", "validated", "rejected"]


class EvidenceReference(BaseModel):
    source_file: str
    row_ref: str                   # e.g. "S1!R12" or "P3-L7"
    excerpt: str = ""              # verbatim text from the source


class QuotedLineItem(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    line_id: str = Field(default_factory=lambda: new_id("line"))
    row_ref: str
    source_description: str
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None          # None means missing, never zero
    price_basis_quantity: Decimal | None = None  # e.g. 100 for "per 100 Nos"
    currency: str | None = None
    line_total: Decimal | None = None
    matched_rfq_item_id: str | None = None
    match_status: LineMatchStatus = "no_match"
    evidence: list[EvidenceReference] = Field(default_factory=list)
    flags: list[ReviewFlag] = Field(default_factory=list)


class Charge(BaseModel):
    kind: Literal["freight", "tax", "discount", "packing", "other"]
    scope: Literal["line", "quote"]
    text: str                      # verbatim
    row_ref: str | None = None


class Quotation(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    quotation_id: str = Field(default_factory=lambda: new_id("quote"))
    source_filename: str
    vendor_name: str | None = None
    quote_reference: str | None = None
    revision: str | None = None
    status: QuotationStatus = "uploaded"
    lines: list[QuotedLineItem] = Field(default_factory=list)
    charges: list[Charge] = Field(default_factory=list)
    flags: list[ReviewFlag] = Field(default_factory=list)
