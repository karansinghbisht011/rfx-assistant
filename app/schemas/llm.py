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
