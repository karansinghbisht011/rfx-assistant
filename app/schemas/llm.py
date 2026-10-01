"""LLM-facing schemas for G1 (parse) and G2 (catalogue resolve). Values are verbatim text."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.rfq import CatalogueCandidate


class ParsedItem(BaseModel):
    original_text: str                 # verbatim slice of the buyer's input for this item
    item_phrase: str                   # the product name in the buyer's words, without quantity or unit
    search_terms: list[str] = Field(default_factory=list)  # alternative catalogue-style names
    quantity_text: str | None = None   # verbatim, e.g. "4", "ten", "a dozen", "10-12"
    unit_text: str | None = None       # verbatim, e.g. "nos", "mtrs", "ltr"
    question: str | None = None


class ParseResult(BaseModel):
    input_class: Literal["procurement_request", "unrelated", "unintelligible"]
    items: list[ParsedItem] = Field(default_factory=list)
    global_question: str | None = None


class ResolveRequest(BaseModel):
    item_index: int
    original_text: str
    item_phrase: str
    candidates: list[CatalogueCandidate]


class Resolution(BaseModel):
    item_index: int
    choice_code: str | None = None     # must be a code from that item's shortlist
    confidence: Literal["high", "medium", "low"] = "low"
    reason: str = ""
    alternatives: list[str] = Field(default_factory=list)


class ResolveResult(BaseModel):
    resolutions: list[Resolution] = Field(default_factory=list)


# Wire schemas: what Gemini is asked to return. No defaults (Gemini's schema support is narrower
# than Pydantic's); converted to the models above after validation.
class WireParsedItem(BaseModel):
    original_text: str
    item_phrase: str
    search_terms: list[str]
    quantity_text: str | None
    unit_text: str | None
    question: str | None


class WireParseResult(BaseModel):
    input_class: Literal["procurement_request", "unrelated", "unintelligible"]
    global_question: str | None
    items: list[WireParsedItem]


class WireResolution(BaseModel):
    item_index: int
    choice_code: str | None
    confidence: Literal["high", "medium", "low"]
    reason: str
    alternatives: list[str]


class WireResolveResult(BaseModel):
    resolutions: list[WireResolution]


# ---- G3 (quote extraction): short field names and optional fields keep the model's answer small and fast.
# Only `ref` and `desc` are required on a line; anything the vendor did not write is left out.
class WireExtractedLine(BaseModel):
    ref: str = Field(description="reference of the row the line came from, copied from the document")
    desc: str = Field(description="product description as written")
    qty: str | None = Field(default=None, description="quantity as written, without the unit")
    unit: str | None = Field(default=None, description="unit as written")
    price: str | None = Field(default=None, description="price for one unit as written, with any currency")
    basis: str | None = Field(default=None, description="only if the price is per N units, e.g. 'per 100 nos'")
    total: str | None = Field(default=None, description="line amount as written")
    cur: str | None = Field(default=None, description="currency as written, or the one in the table or section heading")
    tax: str | None = Field(default=None, description="tax wording for the line or its section")
    moq: str | None = Field(default=None, description="minimum order quantity wording")
    opt: str | None = Field(default=None, description="Option A, Alternate, Optional spare and similar")
    note: str | None = Field(default=None, description="anything else notable, e.g. no price given")
    src: str | None = Field(default=None, description="exact words for this line, ONLY when the row holds several lines")


class WireCharge(BaseModel):
    kind: Literal["freight", "tax", "discount", "packing", "other"]
    scope: Literal["line", "quote"]
    text: str
    ref: str | None = None


class WireExtractedQuote(BaseModel):
    is_quotation: bool
    vendor: str | None = None
    quote_ref: str | None = None
    date: str | None = None
    revision: str | None = None
    validity: str | None = None
    payment: str | None = None
    delivery: str | None = None
    total: str | None = Field(default=None, description="grand total the vendor states, as written")
    lines: list[WireExtractedLine]
    charges: list[WireCharge] | None = None
    warnings: list[str] | None = None


class WireLineMatch(BaseModel):
    line_id: str
    rfq_item_id: str | None
    status: Literal["matched", "possible", "no_match", "extra"]
    differences: list[str]
    is_alternate: bool
    reason: str


class WireMatchResult(BaseModel):
    matches: list[WireLineMatch]


class WirePin(BaseModel):
    item: str                          # an item id from the data, such as "I3"
    vendor: str                        # a vendor id from the data, such as "V2"
    quantity: int | None = None        # leave out for the whole required quantity


class WireProposal(BaseModel):
    """G5: the buyer's request read as rules. The model never writes a figure; code computes every number."""

    reply: str = Field(description="one to three plain sentences about what you understood; no figures")
    allow_split: bool
    every_vendor_supplies: bool
    min_items_per_vendor: int | None = None
    require_vendors: list[str] | None = None
    leave_out_vendors: list[str] | None = None
    max_vendors: int | None = None
    pins: list[WirePin] | None = None
    include_flagged: bool
    assume_rfq_unit: bool
    unsupported: str | None = Field(default=None, description="why the request cannot be answered from the quotations")
    clarifying_question: str | None = None
