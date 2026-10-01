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
from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel, ValidationError

from app import config
from app.services.stream_lines import LineStreamParser
from app.schemas.llm import (
    ParsedItem, ParseResult, Resolution, ResolveRequest, ResolveResult, WireExtractedQuote, WireMatchResult,
    WireParseResult, WireProposal, WireResolveResult,
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

    def extract_quote(self, document_text: str, pdf_bytes: bytes | None = None,
                      on_line: "Callable[[dict], None] | None" = None) -> WireExtractedQuote: ...

    def match_lines(self, rfq_items: list[dict], lines: list[dict]) -> WireMatchResult: ...

    def propose(self, data: str, request: str, history: list[dict], previous_rules: dict | None,
                correction: str | None = None) -> WireProposal: ...


_UNITS = (
    r"nos|no|nr|pcs|pc|pieces?|each|sets?|pairs?|kits?|kgs?|kilos?|tonnes?|tons?|mt|mtrs?|metres?|meters?|m|"
    r"ltrs?|litres?|liters?|l|boxes|box|packs?|packets?|rolls?|drums?"
)
_QTY = r"\d[\d,]*\.?\d*(?:\s*(?:-|–|to)\s*\d[\d,]*\.?\d*)?|(?:a|one|two|three|four|five|six|seven|eight|nine|ten|twelve|twenty)(?:\s+dozen)?|dozen"
_SEGMENT = re.compile(
    rf"^\s*(?:(?P<qty>{_QTY})\s+)?(?:(?P<unit>{_UNITS})\b\s+(?:of\s+)?)?(?P<name>[a-zA-Z].*?)\s*$", re.I
)
_SYNONYMS = {"safety": "protective", "pt": "pressure transmitter", "cable": "cable"}


class NotConfigured(GeminiError):
    """No Gemini key is set, so quotations cannot be read."""


class MockGemini:
    stand_in = True    # the UI shows AI features as unavailable when this is the client
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

    def __init__(self, api_key: str, model: str, *, extract_model: str | None = None, analyst_model: str | None = None,
                 call_limit: int | None = None):
        from google import genai
        from google.genai import types

        self._types = types
        self._model = model
        self._extract_model = extract_model or model
        self._analyst_model = analyst_model or extract_model or model
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

    def _generate(self, system_prompt: str, contents, schema: type[BaseModel], model: str | None = None,
                  on_chunk: Callable[[str], None] | None = None) -> str:
        """One model call with bounded retry. Returns the raw JSON text; never logs content."""
        from google.genai import errors

        types = self._types
        model = model or self._model
        cfg = dict(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=config.MAX_OUTPUT_TOKENS,
        )
        if model.startswith("gemini-2.5"):
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
                if on_chunk is None:
                    response = self._client.models.generate_content(
                        model=model, contents=contents, config=types.GenerateContentConfig(**cfg)
                    )
                else:  # streamed: hand each piece of text to the caller as it arrives
                    pieces, last = [], None
                    for chunk in self._client.models.generate_content_stream(
                        model=model, contents=contents, config=types.GenerateContentConfig(**cfg)
                    ):
                        last = chunk
                        if chunk.text:
                            pieces.append(chunk.text)
                            on_chunk(chunk.text)
                    response = last
                    response_text = "".join(pieces)
            except errors.APIError as exc:
                code = getattr(exc, "code", None)
                _log(f"call {self.calls} failed: HTTP {code} after {time.monotonic() - started:.1f}s")
                if code == 429:
                    raise RateLimited("Gemini rate limit reached") from exc
                if code and code >= 500 and attempt < config.MAX_RETRIES:
                    time.sleep(2)
                    continue
                raise GeminiError(f"Gemini request failed (HTTP {code})") from exc
            elapsed = time.monotonic() - started
            usage = getattr(response, "usage_metadata", None) if response is not None else None
            if usage is not None:  # sizes and speed only, never content
                out = getattr(usage, "candidates_token_count", None) or 0
                _log(f"call {self.calls} ok in {elapsed:.1f}s | {model} | tokens in={getattr(usage, 'prompt_token_count', '?')} "
                     f"out={out} thinking={getattr(usage, 'thoughts_token_count', 0) or 0} | {out / elapsed:.0f} out tok/s")
            else:
                _log(f"call {self.calls} ok in {elapsed:.1f}s")
            finish = response.candidates[0].finish_reason if response is not None and response.candidates else None
            if finish is not None and getattr(finish, "name", str(finish)) != "STOP":
                raise BadResponse(f"Response ended early ({getattr(finish, 'name', finish)})")
            text = response_text if on_chunk is not None else (response.text if response is not None else None)
            if not text:
                raise BadResponse("Empty response")
            return text
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


def _extract(self, document_text: str, pdf_bytes: bytes | None = None,
             on_line: Callable[[dict], None] | None = None) -> WireExtractedQuote:
    prompt = (PROMPTS / "quote_extraction.md").read_text(encoding="utf-8")
    task = f"<document>\n{document_text}\n</document>\n\nTranscribe this quotation." if document_text else "Transcribe this quotation."
    contents = [self._types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"), task] if pdf_bytes else task
    on_chunk = None
    if on_line is not None:
        parser = LineStreamParser()

        def on_chunk(text: str) -> None:  # a preview problem must never fail the read
            try:
                for found in parser.feed(text):
                    on_line(found)
            except Exception:
                pass

    raw = self._generate(prompt, contents, WireExtractedQuote, model=self._extract_model, on_chunk=on_chunk)
    try:
        return WireExtractedQuote.model_validate_json(raw)
    except ValidationError as exc:
        raise BadResponse("Response did not match the schema") from exc


def _match(self, rfq_items: list[dict], lines: list[dict]) -> WireMatchResult:
    prompt = (PROMPTS / "quote_matching.md").read_text(encoding="utf-8")
    task = (f"<rfq_items>{json.dumps(rfq_items, ensure_ascii=False)}</rfq_items>\n"
            f"<quote_lines>{json.dumps(lines, ensure_ascii=False)}</quote_lines>\n\nMatch every quotation line.")
    raw = self._generate(prompt, task, WireMatchResult)
    try:
        return WireMatchResult.model_validate_json(raw)
    except ValidationError as exc:
        raise BadResponse("Response did not match the schema") from exc


def _propose(self, data: str, request: str, history: list[dict], previous_rules: dict | None,
             correction: str | None = None) -> WireProposal:
    prompt = (PROMPTS / "analyst.md").read_text(encoding="utf-8")
    task = (f"<data>{data}</data>\n"
            f"<previous_rules>{json.dumps(previous_rules, ensure_ascii=False) if previous_rules else 'none'}</previous_rules>\n"
            f"<history>{json.dumps(history, ensure_ascii=False)}</history>\n"
            f"<request>{request}</request>")
    if correction:
        task += f"\n\nYour last answer had a problem: {correction} Answer again with valid ids only."
    raw = self._generate(prompt, task, WireProposal, model=self._analyst_model)
    try:
        return WireProposal.model_validate_json(raw)
    except ValidationError as exc:
        raise BadResponse("Response did not match the schema") from exc


LiveGemini.extract_quote = _extract
LiveGemini.match_lines = _match
LiveGemini.propose = _propose


def _log(message: str) -> None:
    print(f"[gemini] {message}", file=sys.stderr, flush=True)


def _mock_extract(self, document_text: str, pdf_bytes: bytes | None = None, on_line=None):
    raise NotConfigured("Reading quotations needs the AI service. Add a Gemini key to enable it.")


def _mock_match(self, rfq_items: list[dict], lines: list[dict]):
    raise NotConfigured("Reading quotations needs the AI service. Add a Gemini key to enable it.")


def _mock_propose(self, data, request, history, previous_rules, correction=None):
    raise NotConfigured("The analyst needs the AI service. Add a Gemini key to enable it.")


MockGemini.extract_quote = _mock_extract
MockGemini.match_lines = _mock_match
MockGemini.propose = _mock_propose


def get_client() -> GeminiClient:
    """LiveGemini when a key and model are configured, otherwise the local stand-in."""
    key = config.get_api_key()
    if key and config.MODEL_LITE:
        limit = os.getenv("GEMINI_CALL_LIMIT")
        _log(f"live client, model {config.MODEL_LITE}")
        return LiveGemini(key, config.MODEL_LITE, extract_model=config.MODEL_EXTRACT or None,
                          analyst_model=config.MODEL_ANALYST or None,
                          call_limit=int(limit) if limit else None)
    _log("no key or model configured: using the local stand-in")
    return MockGemini()
