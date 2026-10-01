from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ids import new_id
from app.schemas.flags import ReviewFlag

MatchStatus = Literal["exact", "fuzzy", "ambiguous", "unmatched"]
RFQStatus = Literal["draft", "ready", "saved"]


class CatalogueCandidate(BaseModel):
    code: str
    title: str
    class_title: str = ""
    default_unit: str = "Nos"
    score: float = 0.0             # retrieval signal, not proof of equivalence


class BuyerDetails(BaseModel):
    """Static mock details for the RFQ PDF; placeholders, not verified customer information."""

    company_name: str = "Example Process Industries Ltd."
    address: str = "Plot 12, Industrial Area, Sample City"
    contact: str = "procurement@example.com"


class RequestedItem(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    item_id: str = Field(default_factory=lambda: new_id("item"))
    original_text: str                         # the buyer's own wording
    catalogue_code: str | None = None
    catalogue_title: str | None = None         # read from the catalogue, never from the model
    quantity: Decimal | None = None            # None means absent; zero is a different thing
    unit: str | None = None                    # canonical unit
    unit_suggested: bool = False               # True while the unit is the catalogue default
    match_status: MatchStatus = "unmatched"
    match_candidates: list[CatalogueCandidate] = Field(default_factory=list)
    flags: list[ReviewFlag] = Field(default_factory=list)


class RFQ(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    rfq_id: str = Field(default_factory=lambda: new_id("rfq"))
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    buyer_details: BuyerDetails = Field(default_factory=BuyerDetails)
    items: list[RequestedItem] = Field(default_factory=list)
    status: RFQStatus = "draft"
    source_session_id: str = ""
