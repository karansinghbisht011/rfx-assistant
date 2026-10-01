"""Exchange rates: a lightweight lookup of ECB reference rates, with a buyer override.

A rate is never invented or silently reused: it carries its source and date, and a failed lookup leaves the
currency without a rate so the comparison says so.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

import httpx
from pydantic import BaseModel, Field

from app import config


class FxRate(BaseModel):
    currency: str
    rate: Decimal                  # units of the comparison currency per 1 unit of `currency`
    source: str                    # "ECB reference rate (Frankfurter)" or "Entered by the buyer"
    as_of: str = ""                # the date the provider publishes the rate for
    retrieved_at: datetime = Field(default_factory=datetime.now)
    manual: bool = False


def valid_rate(rate: Decimal | None) -> bool:
    low, high = config.FX_SANITY_BAND
    return rate is not None and low <= rate <= high


def manual_rate(currency: str, rate: Decimal) -> FxRate | None:
    return FxRate(currency=currency, rate=rate, source="Entered by the buyer", manual=True) if valid_rate(rate) else None


def fetch_rates(currencies: set[str], base: str | None = None) -> dict[str, FxRate]:
    """Rates to the comparison currency for each currency asked, or nothing for those the provider cannot give."""
    base = base or config.COMPARISON_CURRENCY
    out: dict[str, FxRate] = {}
    for currency in sorted(c for c in currencies if c and c != base):
        try:
            transport = httpx.HTTPTransport(local_address="0.0.0.0") if config.FORCE_IPV4 else None
            with httpx.Client(timeout=config.FX_TIMEOUT_SECONDS, transport=transport) as http:
                reply = http.get(config.FX_URL, params={"base": currency, "symbols": base})
            reply.raise_for_status()
            data = reply.json()
            rate = Decimal(str(data["rates"][base]))
        except (httpx.HTTPError, KeyError, ValueError, InvalidOperation, TypeError):
            continue
        if valid_rate(rate):
            out[currency] = FxRate(currency=currency, rate=rate, source="ECB reference rate (Frankfurter)",
                                   as_of=str(data.get("date", "")))
    return out
