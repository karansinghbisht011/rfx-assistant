from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

AnalysisStatus = Literal["not_started", "processing", "needs_review", "complete", "failed"]


class Assumptions(BaseModel):
    """What-if settings shown as chips above the analyst chat. Tools take these as parameters."""

    exclude_vendor_ids: list[str] = Field(default_factory=list)
    include_flagged: bool = False
    use_rfq_unit_for_missing: bool = False
    fx_rate_override: dict[str, Decimal] = Field(default_factory=dict)  # currency -> rate to INR
    max_vendors: int | None = None

    def active(self) -> bool:
        return self != Assumptions()
