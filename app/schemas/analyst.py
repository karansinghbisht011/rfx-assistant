"""The analyst's rules, its answer, and the purchase proposal that code builds from them."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.ids import new_id


class Pin(BaseModel):
    item_id: str
    vendor_id: str
    quantity: Decimal | None = None      # None means the whole required quantity


class ProposalSpec(BaseModel):
    """What the buyer asked for, as rules. Ids are real item and quotation ids (the wire form uses short aliases)."""

    allow_split: bool = False
    every_vendor_supplies: bool = False
    min_items_per_vendor: int | None = Field(default=None, ge=1, le=50)
    require_vendor_ids: list[str] = Field(default_factory=list)
    leave_out_vendor_ids: list[str] = Field(default_factory=list)
    max_vendors: int | None = Field(default=None, ge=1, le=50)
    pins: list[Pin] = Field(default_factory=list)
    include_flagged: bool = False
    assume_rfq_unit: bool = False


class RuleResult(BaseModel):
    text: str
    met: bool
    detail: str = ""


class ProposalRow(BaseModel):
    item_id: str
    item: str
    unit: str
    required_qty: Decimal
    vendor_id: str
    vendor: str
    quantity: Decimal
    unit_price: Decimal                  # per RFQ unit, excluding tax, in the comparison currency
    quoted_price: str = ""               # as the vendor wrote it
    quoted_currency: str = ""            # the currency the vendor quoted in
    total: Decimal


class Proposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: new_id("prop"))
    rows: list[ProposalRow] = Field(default_factory=list)
    grand_total: Decimal | None = None
    currency: str = "INR"
    cheapest_possible_total: Decimal | None = None      # the lowest offer for every item, with no rules
    best_single: tuple[str, Decimal] | None = None      # cheapest vendor that covers every item
    rules: list[RuleResult] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    unfilled: list[str] = Field(default_factory=list)   # item names nobody could supply
    feasible: bool = True


class AnalystTurn(BaseModel):
    turn_id: str = Field(default_factory=lambda: new_id("turn"))
    question: str
    status: Literal["ok", "unsupported", "clarify", "failed"] = "ok"
    reply: str = ""
    spec: ProposalSpec | None = None
    proposal: Proposal | None = None
