"""Gemini access behind a small interface so the app can run against a local stand-in.

LiveGemini calls the Gemini API with schema-constrained JSON and validates every response with
Pydantic. MockGemini is a deterministic, rule-based stand-in used when no key is configured.
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ValidationError

from app import config
from app.schemas.llm import (
    ParsedItem, ParseResult, Resolution, ResolveRequest, ResolveResult, WireParseResult, WireResolveResult,
)

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


class GeminiError(RuntimeError):
    """Base class; messages are safe to log (never contain request text or keys)."""


class RateLimited(GeminiError):
    pass


class BadResponse(GeminiError):
    pass


class CallBudgetExceeded(GeminiError):
    pass


class GeminiClient(Protocol):
    def parse_request(self, text: str) -> ParseResult: ...

    def resolve_items(self, requests: list[ResolveRequest]) -> ResolveResult: ...


_UNITS = (
    r"nos|no|nr|pcs|pc|pieces?|each|sets?|pairs?|kits?|kgs?|kilos?|tonnes?|tons?|mt|mtrs?|metres?|meters?|m|"
    r"ltrs?|litres?|liters?|l|boxes|box|packs?|packets?|rolls?|drums?"
)
_QTY = r"\d[\d,]*\.?\d*(?:\s*(?:-|–|to)\s*\d[\d,]*\.?\d*)?|(?:a|one|two|three|four|five|six|seven|eight|nine|ten|twelve|twenty)(?:\s+dozen)?|dozen"
_SEGMENT = re.compile(
    rf"^\s*(?:(?P<qty>{_QTY})\s+)?(?:(?P<unit>{_UNITS})\b\s+(?:of\s+)?)?(?P<name>[a-zA-Z].*?)\s*$", re.I
)
_SYNONYMS = {"safety": "protective", "pt": "pressure transmitter", "cable": "cable"}


class MockGemini:
    """Splits a request on commas, 'and' and new lines and reads 'quantity unit name' per segment."""

    def parse_request(self, text: str) -> ParseResult:
        segments = [s.strip() for s in re.split(r"[\n;,]| and ", text) if s.strip()]
        items: list[ParsedItem] = []
        for segment in segments:
            match = _SEGMENT.match(segment)
            if not match:
                continue
            name = match.group("name").strip()
            terms = [name]
            swapped = " ".join(_SYNONYMS.get(w.lower(), w) for w in name.split())
            if swapped != name:
                terms.append(swapped)
            items.append(
                ParsedItem(
                    original_text=segment,
                    item_phrase=name,
                    search_terms=terms,
                    quantity_text=match.group("qty"),
                    unit_text=match.group("unit"),
                )
            )
        letters = sum(c.isalpha() for c in text)
        if not items or letters < 0.4 * max(len(text.strip()), 1):
            return ParseResult(input_class="unintelligible")
        return ParseResult(input_class="procurement_request", items=items)

    def resolve_items(self, requests: list[ResolveRequest]) -> ResolveResult:
        results = []
        for req in requests:
            ranked = sorted(req.candidates, key=lambda c: c.score, reverse=True)
            if not ranked or ranked[0].score < config.MATCH_LOW:
                results.append(Resolution(item_index=req.item_index, confidence="low", reason="No close entry"))
                continue
            margin = ranked[0].score - (ranked[1].score if len(ranked) > 1 else 0)
            results.append(
                Resolution(
                    item_index=req.item_index,
                    choice_code=ranked[0].code,
                    confidence="high" if margin >= config.MATCH_MARGIN else "medium",
                    reason="Closest title",
                    alternatives=[c.code for c in ranked[1:4]],
                )
            )
        return ResolveResult(resolutions=results)


class LiveGemini:
    """Real Gemini calls for G1 (parse) and G2 (catalogue resolve)."""

    def __init__(self, api_key: str, model: str, *, call_limit: int | None = None):
        from google import genai
        from google.genai import types

        self._types = types
        self._model = model
        client_args = {}
        if config.FORCE_IPV4:
            import httpx

            client_args["transport"] = httpx.HTTPTransport(local_address="0.0.0.0")
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=config.API_TIMEOUT_SECONDS * 1000,
                client_args=client_args or None,
                retry_options=types.HttpRetryOptions(attempts=1),  # retries are ours, so rate limits are never hammered
            ),
        )
        self.calls = 0
        self._limit = call_limit

    def _generate(self, system_prompt: str, contents: str, schema: type[BaseModel]) -> str:
        """One model call with bounded retry. Returns the raw JSON text; never logs content."""
        from google.genai import errors

        types = self._types
        cfg = dict(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=config.MAX_OUTPUT_TOKENS,
        )
        if self._model.startswith("gemini-2.5"):
            cfg["temperature"] = config.GENERATION_TEMPERATURE
            cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        else:  # Gemini 3.x: default temperature is recommended; keep reasoning minimal for speed and cost
            cfg["thinking_config"] = types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL)
        for attempt in range(config.MAX_RETRIES + 1):
            if self._limit is not None and self.calls >= self._limit:
                raise CallBudgetExceeded(f"Call budget of {self._limit} reached")
            self.calls += 1
            started = time.monotonic()
            try:
                response = self._client.models.generate_content(
                    model=self._model, contents=contents, config=types.GenerateContentConfig(**cfg)
                )
            except errors.APIError as exc:
                code = getattr(exc, "code", None)
                _log(f"call {self.calls} failed: HTTP {code} after {time.monotonic() - started:.1f}s")
                if code == 429:
                    raise RateLimited("Gemini rate limit reached") from exc
                if code and code >= 500 and attempt < config.MAX_RETRIES:
                    time.sleep(2)
                    continue
                raise GeminiError(f"Gemini request failed (HTTP {code})") from exc
            _log(f"call {self.calls} ok in {time.monotonic() - started:.1f}s")
            finish = response.candidates[0].finish_reason if response.candidates else None
            if finish is not None and getattr(finish, "name", str(finish)) != "STOP":
                raise BadResponse(f"Response ended early ({getattr(finish, 'name', finish)})")
            if not response.text:
                raise BadResponse("Empty response")
            return response.text
        raise GeminiError("Gemini request failed")

    def parse_request(self, text: str) -> ParseResult:
        prompt = (PROMPTS / "rfq_parse.md").read_text(encoding="utf-8")
        raw = self._generate(prompt, f"<request>\n{text}\n</request>\n\nExtract the items.", WireParseResult)
        try:
            return ParseResult.model_validate(WireParseResult.model_validate_json(raw).model_dump())
        except ValidationError as exc:
            raise BadResponse("Response did not match the schema") from exc

    def resolve_items(self, requests: list[ResolveRequest]) -> ResolveResult:
        prompt = (PROMPTS / "catalogue_resolve.md").read_text(encoding="utf-8")
        resolutions: list[Resolution] = []
        for start in range(0, len(requests), config.RESOLVE_BATCH_SIZE):
            batch = requests[start : start + config.RESOLVE_BATCH_SIZE]
            payload = [
                {
                    "item_index": r.item_index,
                    "buyer_wording": r.original_text,
                    "product_name": r.item_phrase,
                    "candidates": [{"code": c.code, "title": c.title, "class": c.class_title} for c in r.candidates],
                }
                for r in batch
            ]
            raw = self._generate(
                prompt, f"<items>{json.dumps(payload, ensure_ascii=False)}</items>\n\nChoose for every item.",
                WireResolveResult,
            )
            try:
                wire = WireResolveResult.model_validate_json(raw)
            except ValidationError as exc:
                raise BadResponse("Response did not match the schema") from exc
            resolutions += [Resolution.model_validate(r.model_dump()) for r in wire.resolutions]
        return ResolveResult(resolutions=resolutions)


def _log(message: str) -> None:
    print(f"[gemini] {message}", file=sys.stderr, flush=True)


def get_client() -> GeminiClient:
    """LiveGemini when a key and model are configured, otherwise the local stand-in."""
    key = config.get_api_key()
    if key and config.MODEL_LITE:
        limit = os.getenv("GEMINI_CALL_LIMIT")
        _log(f"live client, model {config.MODEL_LITE}")
        return LiveGemini(key, config.MODEL_LITE, call_limit=int(limit) if limit else None)
    _log("no key or model configured: using the local stand-in")
    return MockGemini()
