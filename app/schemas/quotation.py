from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ids import new_id
from app.schemas.flags import ReviewEntry, ReviewFlag

LineMatchStatus = Literal["matched", "possible", "no_match", "extra"]
QuotationStatus = Literal["uploaded", "parsed", "needs_review", "validated", "rejected", "failed"]
TaxBasis = Literal["inclusive", "exclusive", "unclear"]


class EvidenceReference(BaseModel):
    source_file: str
    row_ref: str                   # e.g. "Offer!R12" or "P3-T1R4"
    excerpt: str = ""              # verbatim text from the source


class QuotedLineItem(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    line_id: str = Field(default_factory=lambda: new_id("line"))
    row_ref: str = ""
    source_quote: str = ""                       # verbatim text of the row the model read
    source_description: str = ""
    # as written by the vendor
    quantity_text: str | None = None
    unit_text: str | None = None
    unit_price_text: str | None = None
    price_basis_text: str | None = None
    line_total_text: str | None = None
    currency_text: str | None = None
    tax_text: str | None = None
    lead_time_text: str | None = None
    moq_text: str | None = None
    option_label: str | None = None
    remarks: str | None = None
    # parsed by code (None means absent, never zero)
    quantity: Decimal | None = None
    unit: str | None = None                      # canonical, or a convertible quote-side unit
    unit_price: Decimal | None = None
    price_basis_quantity: Decimal | None = None  # e.g. 100 for "per 100 Nos"
    currency: str | None = None
    line_total: Decimal | None = None
    moq: Decimal | None = None
    # matching
    matched_rfq_item_id: str | None = None
    match_status: LineMatchStatus = "no_match"
    match_differences: list[str] = Field(default_factory=list)
    is_alternate: bool = False
    match_reason: str = ""
    match_score: float = 0.0
    # review
    excluded: bool = False
    acknowledged: list[str] = Field(default_factory=list)
    flags: list[ReviewFlag] = Field(default_factory=list)

    @property
    def price_per_unit(self) -> Decimal | None:
        """Unit price after the stated price basis ("per 100" means divide by 100)."""
        if self.unit_price is None:
            return None
        return self.unit_price / (self.price_basis_quantity or Decimal(1))


class Charge(BaseModel):
    kind: Literal["freight", "tax", "discount", "packing", "other"]
    scope: Literal["line", "quote"]
    text: str                      # verbatim
    row_ref: str | None = None


class Quotation(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    quotation_id: str = Field(default_factory=lambda: new_id("quote"))
    source_filename: str
    file_hash: str = ""
    uploaded_at: datetime = Field(default_factory=datetime.now)
    status: QuotationStatus = "uploaded"
    reject_reason: str | None = None
    excluded: bool = False                       # the buyer left this whole quotation out
    # vendor and terms (text as written, plus parsed values)
    vendor_name: str | None = None
    quote_reference: str | None = None
    revision: str | None = None
    quote_date: date | None = None
    quote_date_text: str | None = None
    validity_text: str | None = None
    validity_until: date | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    stated_total_text: str | None = None
    stated_total: Decimal | None = None
    currency: str | None = None                  # the quote's main currency
    tax_basis: TaxBasis = "unclear"
    # content
    lines: list[QuotedLineItem] = Field(default_factory=list)
    charges: list[Charge] = Field(default_factory=list)
    source_rows: dict[str, str] = Field(default_factory=dict)   # row_ref -> text, for evidence
    read_from_image: bool = False
    table_row_count: int = 0
    hidden_sheets: list[str] = Field(default_factory=list)
    uncached_formulas: int = 0
    notes: list[str] = Field(default_factory=list)
    # review
    acknowledged: list[str] = Field(default_factory=list)     # quote-level flag codes accepted
    flags: list[ReviewFlag] = Field(default_factory=list)
    review_log: list[ReviewEntry] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.vendor_name or self.source_filename
