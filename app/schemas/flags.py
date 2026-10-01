from typing import Literal

from pydantic import BaseModel, Field

from app.ids import new_id

Severity = Literal["block", "review", "info"]
Scope = Literal["rfq", "rfq_item", "file", "vendor", "quote_line", "match", "analysis"]
Resolution = Literal["accepted", "edited", "excluded"]


class ReviewEntry(BaseModel):
    """One line of the Review summary. It stays listed and changes state: open, reviewed (accepted), fixed (edited)."""

    key: str                       # "<scope_id>:<code>"
    code: str
    scope_id: str
    message: str
    blocking: bool = False         # must be fixed by editing; cannot be accepted
    status: Literal["open", "reviewed", "fixed"] = "open"


class ReviewFlag(BaseModel):
    """One entry in the Review summary. Flags are kept and shown; nothing is silently dropped."""

    flag_id: str = Field(default_factory=lambda: new_id("flag"))
    code: str                      # verifier ID, e.g. "R6" or "Q22"
    severity: Severity
    scope: Scope
    scope_id: str
    message: str                   # plain language for a procurement user
    resolution: Resolution | None = None

    @property
    def open(self) -> bool:
        return self.resolution is None
