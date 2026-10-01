# Implementation Plan

## 1. Purpose and Scope

This document translates the product requirements into an implementation-ready plan for a lightweight procurement application. It covers architecture, components, workflows, data contracts, AI integration, user experience, validation, security, testing, and deployment.

The application supports three workflows:
1. **Generate an RFQ** from a buyer's natural-language request.
2. **Manage My RFQs** by viewing, downloading, and selecting RFQs saved during the current session.
3. **Evaluate Quotations** by uploading vendor quotations against a selected RFQ and reviewing structured comparisons and analysis.

The initial domain context is MRO procurement for refinery and process-plant environments. The primary user is a Procurement Manager; maintenance and instrumentation stakeholders may contribute technical requirements.

### MVP boundaries

**Included:** natural-language RFQ drafting; catalogue-backed item suggestions; clarification; editable line items; RFQ PDF export; session-only RFQ storage; multiple quotation uploads; document parsing; AI-assisted extraction and matching; deterministic price/currency comparison; a Review summary of every flagged item; an analyst that turns a plain-language request into a Purchase Proposal (cheapest purchase under the buyer's rules, split purchases allowed), calculated by code; basic Streamlit deployment.

**Excluded:** accounts, roles, approvals, durable database storage, persistent history, supplier portals, ERP integrations, purchase-order issuance, autonomous supplier communication or award decisions, voice input, paid/always-on production hosting, vector databases, agent frameworks (the analyst is one structured model call plus an exact solver in our own code), downloads of the analysis (no analysis PDF or export), image and legacy `.doc`/`.xls` uploads, and email ingestion (an emailed quotation is supplied as a `.docx`).

### Principles

- **AI interprets; application code controls.** Gemini handles language understanding, extraction, clarification, and grounded synthesis. Application code owns validation, catalogue integrity, state, calculations, and output generation.
- **No fabricated catalogue records.** Matches must originate from the supplied catalogue. Unmatched items remain visible for buyer review.
- **Human-in-the-loop.** The buyer reviews and edits RFQs, confirms vendor identity and quote revision, and makes sourcing decisions.
- **Explainable results.** Show source values, match status, assumptions, evidence, and exceptions.
- **Keep the MVP small.** Add infrastructure only when it demonstrably improves reliability or usability.
- **Stateless by design.** No database and no persistence. A browser refresh or session expiry clears RFQs, uploads, and analysis. Evaluation always uses the RFQ saved in the same session.

## 2. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────┐
│                    Streamlit User Interface                 │
│ Generate an RFQ | Manage My RFQs | Evaluate Quotations      │
└──────────────────────────────┬─────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────┐
│                 Application Workflow Controller             │
│ session state · validation · routing · errors                │
└──────────────┬────────────────────────────────┬─────────────┘
               │                                │
┌──────────────▼──────────────┐   ┌─────────────▼────────────┐
│ RFQ Workflow                │   │ Quote Evaluation         │
│ Gemini parse/resolve        │   │ File parsing             │
│ Catalogue search            │   │ Gemini extraction/match  │
│ Buyer edits/validation      │   │ Validation/review        │
└──────────────┬──────────────┘   └─────────────┬────────────┘
               │                                │
┌──────────────▼──────────────┐   ┌─────────────▼────────────┐
│ Static UNSPSC catalogue     │   │ Deterministic comparison │
│ + in-memory search index    │   │ and sourcing scenarios  │
└─────────────────────────────┘   └─────────────┬────────────┘
                                                │
                                  ┌─────────────▼────────────┐
                                  │ Analyst Q&A and PDF      │
                                  └──────────────────────────┘

External services: Google Gemini API; lightweight exchange-rate lookup;
Streamlit Community Cloud for basic demo hosting.
```

### Component responsibilities

| Component | Responsibility | Implementation notes |
|---|---|---|
| Streamlit UI | Three-tab experience, forms, tables, uploads, chat, downloads | Keep presentation separate from business logic. |
| Workflow controller | Route actions and manage state | Explicit transitions and user-visible errors. |
| RFQ service | Parse, search, resolve, validate, and save RFQs | Orchestrates G1/G2 and the catalogue service. |
| Catalogue service | Load, normalize, and search catalogue | Static file; cached in memory. |
| Document ingestion | Validate and parse quote files | Format-specific adapters and bounded processing. |
| Quote extraction | Extract quote data (G3) | Verbatim text values, row references, uncertainty. |
| Quote matching | Map quote lines to RFQ items | Code first; G4 only for lines code cannot match confidently. |
| Verifiers | Check parsed files and every Gemini output; produce Review flags | Pure functions, unit-tested (section 13). |
| Comparison engine | Calculate prices and scenarios | Deterministic Python; no LLM arithmetic/ranking. |
| Analyst service | Reads a request as rules (G5) and builds the Purchase Proposal | The model sets rules from enums and ids only; the allocation solver and every figure are code. |
| PDF service | Generate the RFQ PDF | Static mock buyer/company details. |
| Session store | Hold current-session RFQs and analysis | Streamlit session state and temporary files only. |

### Repository structure

```text
RFx Assistant/
├── app/
│   ├── main.py                      # Streamlit entry point
│   ├── config.py
│   ├── state.py
│   ├── schemas/{rfq.py,quotation.py,analysis.py,flags.py}
│   ├── services/
│   │   ├── gemini_client.py
│   │   ├── rfq_service.py
│   │   ├── catalogue_service.py
│   │   ├── units.py
│   │   ├── document_ingestion.py
│   │   ├── quote_extraction.py
│   │   ├── quote_matching.py
│   │   ├── verifiers.py
│   │   ├── comparison.py
│   │   ├── fx.py
│   │   ├── allocation.py
│   │   ├── analyst_service.py
│   │   └── pdf_service.py
│   ├── prompts/{rfq_parse.md,catalogue_resolve.md,quote_extraction.md,quote_matching.md,analyst.md}
│   └── ui/{rfq_tab.py,manage_rfqs_tab.py,evaluate_quotes_tab.py,analyst_panel.py,components.py}
├── data/unspsc_catalogue.csv        # golden record (section 7)
├── docs/{PRD.md,implementation.md}
├── tests/
├── .streamlit/config.toml
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md                        # written last
└── CLAUDE.md
```

Keep prompts, parsing, calculations, verifiers, and UI independently testable.

## 3. Technology Stack

| Layer | Proposed choice | Rationale |
|---|---|---|
| Language | Python 3.12+ | Mature data/document ecosystem. |
| UI | Streamlit | Rapid interactive prototype development. |
| LLM | Google Gemini API via the Google Gen AI Python SDK (`google-genai`) only | Structured extraction, document understanding, and function calling for the analyst. No other AI library. |
| Validation | Pydantic | Typed contracts and response validation. |
| Data | pandas, openpyxl | CSV/Excel ingestion and normalization. |
| Catalogue matching | RapidFuzz + exact-title matching | Efficient search without a vector database. |
| PDF parsing | PyMuPDF | Digital PDF text extraction; scanned PDFs go to Gemini natively. |
| Word parsing | python-docx | DOCX extraction. |
| Exchange rates | httpx + Frankfurter (ECB data, free, no key) | Lightweight lookup with a buyer override. |
| PDF generation | ReportLab | Downloadable RFQ and analysis documents. |
| Configuration | python-dotenv locally; Streamlit secrets in deployment | Secrets outside source code. |
| Tests | pytest | Unit, integration, and workflow coverage. |
| Hosting/source control | Streamlit Community Cloud; Git/GitHub | Basic demo deployment and version control. |

No agent framework, vector DB, or paid infrastructure. The analyst is one structured `google-genai` call; the purchase optimisation uses `scipy.optimize.milp` (HiGHS), the one numeric dependency, chosen over hand-written search for exactness with split quantities, minimum shares and vendor limits.

## 4. Configuration, Secrets, and Gemini

### Configuration

Centralize settings in `src/config.py`: model ID, generation parameters, token/time limits, upload limits, catalogue path, supported extensions, exchange-rate provider/timeout, PDF settings, matching thresholds, and analyst limits (question length, history, context size, session call cap). Do not scatter model IDs or thresholds through UI code.

### API credentials

- Read the Gemini API key from an environment variable locally and Streamlit secrets in deployment.
- Never expose credentials to the browser, place them in downloads, or commit them.
- Include `.env.example` with variable names and placeholders only.
- A Gemini Pro subscription should not be assumed to include Gemini API credits or quota; verify API project access and billing separately.

### Model strategy

Use a currently available stable Gemini Flash model that supports required structured output and document modalities. Keep the model ID configurable and verify access, quotas, limits, and pricing at implementation time.

Initial settings:
- Temperature around `0.1–0.2` for extraction and matching.
- Low/minimal thinking initially; do not enable extended/high thinking by default.
- Schema-constrained JSON where supported, validated with Pydantic.
- Explicit timeouts, bounded retries for transient failures, and one limited repair attempt for invalid structured output.
- Increase reasoning effort only if observed quality problems justify the added latency and cost.
- Per-call model tiers, schemas, and prompt practices are specified in section 12.

Do not assume a particular model ID, free tier, quota, context-caching feature, or price will remain available.

### Prompt and context caching

Caching is optional. Use it only if supported by the selected API and beneficial under measured usage. Stable system instructions and schemas may be cache candidates. Do not cache confidential quotations or session-specific buyer data by default. Retrieve only relevant catalogue candidates instead of passing the entire catalogue. Version prompts under `src/prompts/` and record prompt/model versions in non-sensitive diagnostics; avoid logging raw document contents.

## 5. Data Contracts

Pydantic models are the canonical application contracts. Treat model output as untrusted until validated. Define explicit nested types for buyer details, catalogue candidates, evidence references, comparable prices, exclusions, allocations, and currency-rate evidence. Use `Decimal` for money and quantities where precision matters; use `Field(default_factory=...)` for mutable defaults.

Illustrative RFQ item:

```python
class RequestedItem(BaseModel):
    item_id: str
    original_text: str                        # the buyer's own wording
    catalogue_code: str | None = None
    catalogue_title: str | None = None        # read from the catalogue, never from the model
    quantity: Decimal | None = None
    unit: str | None = None                   # canonical unit (section 7)
    unit_suggested: bool = False              # True while the unit is the catalogue default_unit
    match_status: Literal["exact", "fuzzy", "ambiguous", "unmatched"]
    match_candidates: list[CatalogueCandidate] = Field(default_factory=list)
    flags: list[ReviewFlag] = Field(default_factory=list)
```

Illustrative RFQ:

```python
class RFQ(BaseModel):
    rfq_id: str
    name: str
    created_at: datetime
    buyer_details: BuyerDetails               # static mock details
    items: list[RequestedItem]
    status: Literal["draft", "ready", "saved"]
    source_session_id: str
```

Illustrative quotation line (built from the G3 output after code parses the verbatim text):

```python
class QuotedLineItem(BaseModel):
    line_id: str
    row_ref: str
    source_description: str
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    price_basis_quantity: Decimal | None = None   # e.g. 100 for "per 100 Nos"
    currency: str | None = None
    line_total: Decimal | None = None
    matched_rfq_item_id: str | None = None
    match_status: Literal["matched", "possible", "no_match", "extra"]
    evidence: list[EvidenceReference] = Field(default_factory=list)
    flags: list[ReviewFlag] = Field(default_factory=list)
```

Quotation, comparison, and scenario models should additionally capture vendor identity, quotation reference/revision, source filename, processing status, per-item eligibility, exclusions, original and normalized prices, currency rate/source/timestamp, vendor allocations, assumptions, exceptions, and analysis timestamp.

## 6. Session State and Lifecycle

The MVP has no database. Store the RFQ draft, clarification state, session-saved RFQs, uploaded-file metadata, parsed quotations, vendor/revision confirmations, selected RFQ, analysis results, and analysis conversation in `st.session_state`. Use stable IDs for RFQs, items, quotations, and quote lines; do not use display names as keys.

**Lifecycle rules:**
- Saved RFQs and analysis exist only during the active session.
- A fresh session starts without prior RFQs or analysis history.
- Uploaded files are temporary and should be cleaned up when feasible.
- Do not imply persistence or recovery after session loss.
- A browser refresh ends the session and clears everything. This is intentional for the MVP.
- Quotation evaluation uses the RFQ saved in the same session.

Use explicit state transitions:
- RFQ: `draft → ready → saved` (unresolved points are Review flags, not a separate state)
- Quotation: `uploaded → parsed → needs_review → validated` or `rejected`
- Analysis: `not_started → processing → needs_review → complete` or `failed`

Reject invalid transitions in application logic and show recoverable feedback.

## 7. Catalogue, Search, and Units

### Source and loading

`data/unspsc_catalogue.csv` is the golden record. It holds 13,326 commodity rows derived from UNSPSC v26.0801 (source: https://www.ungm.org/Public/UNSPSC), limited to 17 segments relevant to refinery and process-plant MRO purchasing (12, 13, 15, 20, 22, 23, 24, 26, 27, 30, 31, 32, 39, 40, 41, 46, 47). The commodity title is the item name the buyer sees; it plays the role of a SKU name. The original workbook is not part of the repository, and corrections are made in the CSV directly.

Columns: `commodity_code`, `commodity_title`, `class_title`, `family_title`, `segment_title`, `definition` (present for about half the rows), and `default_unit`. `default_unit` is a keyword-rule suggestion and not source data, so it is always shown as a suggestion the buyer can change. The catalogue carries no synonym or acronym data.

At startup: load with pandas (all columns as strings), validate required columns, unique codes, and that every `default_unit` is canonical; normalize titles and definitions for search; cache with `st.cache_resource`. If loading fails, disable RFQ generation and show an actionable error.

### Search pipeline

1. Normalize G1's `search_terms` and the item phrase.
2. An exact normalized title match resolves the item as `exact`.
3. Otherwise RapidFuzz (token-set and weighted ratios) scores the terms against commodity titles, with definitions as a weaker signal, and returns the top 8 candidates with scores.
4. One clear winner (score at or above `MATCH_HIGH` and a margin of at least `MATCH_MARGIN` over the runner-up) is resolved by code as `fuzzy` and skips G2. Otherwise G2 chooses among the candidates. A best score below `MATCH_LOW` leaves the item `unmatched` with candidates in the picker.

Thresholds live in `config.py` and are tuned by hand against real queries while building. Scores are retrieval signals, not proof of equivalence. Statuses: `exact`, `fuzzy`, `ambiguous`, `unmatched`.

### Unmatched items

Retain the original wording, mark `unmatched`, flag buyer review, and do not fabricate a catalogue code, title, or unit. Allow the buyer to save only after explicitly acknowledging the item.

### Units

Canonical units for RFQ lines: **Nos, Set, Pair, Kit, Kg, Tonne, Metre, Litre, Box, Pack, Roll, Drum**.

- **Aliases** map common spellings to canonical units (`nos`, `pcs`, `each`, `ea` to Nos; `mtr`, `mtrs`, `meter` to Metre; `ltr`, `liter` to Litre; `kgs` to Kg; `MT` and `ton` to Tonne). Unmapped units are flagged, never guessed.
- **Conversions** exist only within a physical dimension, using exact factors: mass (1 Tonne = 1000 Kg = 1,000,000 g), length (1 Metre = 100 cm = 1000 mm; 1 km = 1000 Metre), volume (1 Litre = 1000 ml; 1 kl = 1000 Litre). Gram, cm, mm, km, ml, and kl are accepted on the quote side and converted to the RFQ unit.
- **Count units** (Nos, Set, Pair, Kit, Box, Pack, Roll, Drum) are not interconvertible, because a Box or Pack has no fixed size. A quote in a different count unit is incomparable and flagged for the buyer.
- **Price basis** ("per 100", "per 1000", "per kg") is not a unit. It is parsed into `price_basis_quantity` and the unit price is normalized from it.
- The catalogue's `default_unit` is shown on a new RFQ line as a suggestion when the buyer states no unit.

## 8. Workflow A — Generate an RFQ

### User journey

1. Buyer enters a natural-language procurement request.
2. Validate non-empty input and configured length limits.
3. G1 parses the request into distinct items with verbatim quantity and unit text and catalogue-style search terms.
4. Validate the response with Pydantic and run the RFQ verifiers.
5. Code shortlists catalogue candidates per item; items with one clear winner are resolved by code, and G2 chooses among candidates for the rest.
6. Flag missing quantities, unclear units, ambiguous matches, and unmatched items in the Review summary.
7. Resolve flags in the interface: a picker for ambiguous catalogue entries and editable cells for quantity and unit. Free-text clarification is used only for input G1 could not parse.
8. Render an editable table for buyer review.
9. Buyer edits, saves, and downloads the RFQ PDF.

### Editable table

Columns: **Item**, **Quantity**, **Unit**. The item cell displays catalogue terminology when matched; unmatched items retain original wording and a visible review flag. Support catalogue search/replacement, quantity/unit edits, line removal, duplicate review, status badges, and access to the buyer's original wording.

### Quantity/unit validation

- Missing quantity remains blank and triggers a visible prompt; never infer/default it.
- Require a valid positive quantity for every line before finalization.
- When the buyer states no unit, show the catalogue `default_unit` with a "suggested" badge. It is never applied silently; every line must carry a visible unit before saving.
- Preserve buyer-stated units; store normalized units separately if a trusted conversion is applied.

### RFQ name and PDF

Default the name to `RFQ-YYYY-MM-DD` using the application date; append a short suffix if the name already exists in the active session. Let the buyer edit the name. The PDF includes static mock buyer/company details, RFQ name/date, line items, quantities, units, and relevant review notes. Clearly treat mock details as placeholders, not verified customer information.

### RFQ Gemini calls

The RFQ workflow uses two calls: **G1 (parse)** and **G2 (catalogue resolve)**, specified in section 12. Both outputs pass the RFQ verifiers (R1–R19, section 13) before reaching state.

The application—not Gemini—performs catalogue search, quantity validation, ID generation, state transitions, and PDF creation.

### Gibberish/unrelated input

Do not create a blank or fabricated RFQ. Ask the buyer to describe items, quantities, and units. Preserve useful text for editing. Avoid repeated model calls on unchanged invalid input; require an edit or explicit retry.

## 9. Workflow B — Manage My RFQs

Provide a session-only list, newest first, with summary tiles (RFQs saved, line items, latest) and one rich row per RFQ: name, created date and time, reference, line count with a preview of the first items, status chips (Saved, how many entries were fixed or accepted, Selected), and the actions below. **View** expands the full item table in place. MVP actions are **View**, **PDF download**, and **Select for evaluation** (which selects the RFQ and opens Evaluate Quotations). Do not add persistence, collaboration, approvals, or complex lifecycle features. Show an empty state directing the buyer to the RFQ builder when no RFQs are saved.

## 10. Workflow C — Evaluate Quotations

### User journey

1. Buyer selects a finalized RFQ from the active session.
2. Buyer uploads multiple vendor quotation files.
3. Validate each file independently; valid files continue even if another file fails.
4. Parse content into normalized text/table structures with row references; scanned PDFs go to Gemini natively.
5. G3 extracts vendor metadata, lines, and charges as verbatim text; code parses the values and runs the quote verifiers; code matches confident lines to RFQ items and G4 handles only the rest; the matching verifiers run.
6. Buyer reviews the Review summary and confirms vendor identity, quotation reference/revision, and flagged lines or mappings.
7. Buyer selects one version per vendor.
8. Deterministic code calculates eligible item comparisons and indicative sourcing scenarios.
9. Show the Compare step: the Purchase Proposal and the analyst chat, the lowest offer per item, and vendor totals. There is no analysis download.

### Guided steps (built)

The step bar (Select RFQ, Upload, Review, Compare), upload with a live analysis screen, the review step (alignment matrix, per-vendor flags, Accept and Exclude), and the Compare step with the analyst are built. Files are read one after another with a short pause so a free-tier rate limit is not hit; a file that hits a rate limit is kept and can be retried without being re-uploaded. The design below is the original plan.

Evaluate Quotations is presented as five steps on one page, with a step bar (done, active, upcoming), Back and Next buttons, and progress kept in session state: **Select RFQ**, **Upload**, **Review**, **Compare**, **Ask**. Each step unlocks when the one before it is complete: Upload needs a selected RFQ, Review needs at least one parsed quotation, Compare needs every quotation validated or its flags resolved, and Ask needs a computed analysis. A locked step shows a one-line reason instead of its content. Arriving from Manage's **Select for evaluation** lands on Upload with the RFQ already chosen. The step bar is a reusable component (`app/ui/stepper.py`), built in Phases 4 and 5 with the steps themselves.

### Supported formats

CSV, TSV, Excel (`.xlsx`), PDF, and Word (`.docx`). An emailed quotation is supplied as a `.docx`. Legacy `.xls` and `.doc` files, images, and other formats are rejected with a message to save as `.xlsx` or `.docx` and the supported-format list.

### Per-file validation

Check extension/type, size, empty/unreadable content, parse errors, duplicates, page/row limits, and encrypted/malformed files. Show each file's processing state and a reason plus replace/remove action for rejections. One invalid file must not block valid uploads. Do not assume a file is a quotation until content is inspected.

### Parsing

Use deterministic parsers first: pandas for CSV/TSV; openpyxl for `.xlsx` (preserve sheet and row context); PyMuPDF for digital PDFs; python-docx for `.docx`, including paragraphs outside tables. Every row or paragraph gets a stable reference. Detect scanned or image-only PDFs by low or no extracted text and send them to Gemini natively within the page limit, marking the output as read from an image. Preserve page-level evidence and flag low-confidence extraction.

### Vendor and revision confirmation

Allow confirmation/correction of vendor identity and review of quote reference, date, and revision. Detect possible duplicate/superseded versions and require buyer selection of one version per vendor. Never combine revisions automatically.

### Quote Gemini calls

Quote evaluation uses **G3 (extraction)** and **G4 (matching, only for lines code cannot match)**, specified in section 12, and **G5 (the analyst)** after analysis. Extraction and matching are separate on purpose: G3 sees only the document, so it cannot bend lines toward expected items, and matching can be re-run cheaply when the buyer corrects a line. Outputs pass the Q, M, and A verifiers (section 13).

Gemini must not calculate final totals, rank vendors, convert currencies, or choose sourcing scenarios. Those are deterministic application functions.

## 11. Comparison and Sourcing Logic

### Comparison rules

- Compare only eligible, sufficiently matched quote lines.
- Compare prices only when quantities and units are comparable or a trusted deterministic conversion exists.
- Do not silently assume packaging, unit equivalence, technical equivalence, or specification compliance.
- The comparison basis is **unit price × RFQ quantity, excluding tax**. Stated line discounts are applied only when clearly tied to the line; taxes, freight, packing, and quote-level discounts are extracted and shown beside the price, never silently added or assumed to be zero. Tax-inclusive quotes are flagged, and tax is backed out only when the rate is stated explicitly.
- Preserve original values alongside normalized values. Exclude incomplete/incomparable values from rankings.

### Currency normalization

Use a lightweight exchange-rate lookup, not LLM web research. Preserve original amount/currency, converted amount/target currency, rate, source/provider, retrieval timestamp, and warnings. If lookup fails, retain the source currency/value, exclude it from INR-based ranking/totals, and explain that cross-currency comparison is incomplete. Never invent or silently reuse a rate.

### Deterministic comparison engine

1. Validate quote-line mapping and eligibility.
2. Normalize units only where a trusted conversion rule exists.
3. Convert eligible values to the comparison currency only with a verified rate.
4. Calculate the lowest eligible vendor price per RFQ item.
5. Calculate the cheapest comparable single-vendor quote covering all required items.
6. Calculate an indicative hybrid allocation using the lowest eligible offer per item.
7. Record exclusions, missing data, currency gaps, assumptions, and deviations.
8. Return a typed analysis object.

Use `Decimal` and explicit rounding rules; retain raw and normalized values separately.

Expose the engine as pure functions parameterized by assumptions (vendor filter, include flagged lines, use the RFQ unit for unstated units, exchange-rate override, maximum number of vendors), so the same code serves the main analysis and the analyst's what-if tools. A maximum-vendor constraint is solved by searching vendor subsets (a few vendors, so exhaustive search is cheap).

### Single-vendor and hybrid scenarios

For a single-vendor scenario, include a vendor only if it has eligible comparable prices for all required RFQ items; otherwise mark the scenario incomplete/ineligible and explain why. Return the lowest-cost **comparable** single-vendor scenario, without implying price alone determines award suitability.

For the indicative hybrid scenario, allocate each RFQ line to the vendor with the lowest eligible comparable offer and sum the line-level costs. Label it as an **indicative lowest-cost hybrid combination**, not a final recommendation or award. Show allocations and all assumptions/exclusions. If any RFQ line lacks an eligible price, mark the scenario incomplete.

### Analysis UI, Q&A, and PDF

Show vendors processed, quotations requiring review, item-level lowest eligible prices, side-by-side comparisons, single-vendor and hybrid scenarios, missing/extra/unmatched lines, specification deviations, uncertainty, exclusions, and currency-rate evidence.

The Compare step is two columns. The left column shows the **Purchase Proposal** (or an empty state with example requests), then **Lowest offer for each item** and **Vendor totals**, then a collapsed list of lines left out of the comparison and a small exchange-rate panel. The right column is the analyst chat. There is no assumptions panel: assumptions are rules the analyst sets from the buyer's request and shows back. The analysis has no download.

## 12. Gemini Call Specifications

Gemini is called at five points. Every call has one job, a small schema, and a verifier pass (section 13) before its output reaches application state. The schemas below are the LLM-facing contracts; the application contracts in section 5 add IDs, catalogue data, and review flags on top of them.

| # | Call | Input | Output | Model tier | When |
|---|---|---|---|---|---|
| G1 | RFQ parse | Buyer's text (plus any free-text clarification) | Items with verbatim quantity/unit text and catalogue-style search terms | Low-cost (Flash-Lite class) | Once per submitted request |
| G2 | Catalogue resolve | Each unresolved item plus its shortlist of up to 8 catalogue candidates | One choice from the shortlist, or null with a question | Low-cost | Once per request, batched; skipped for items the application resolves on its own |
| G3 | Quote extraction | One vendor file, parsed with row references | Vendor metadata, quote lines (verbatim text values), charges | Mid (Flash class; multimodal) | Once per file |
| G4 | Quote-to-RFQ matching | The RFQ items and the vendor lines code could not match confidently (text only) | A mapping with status, reason, and visible differences | Low-cost | Only when needed, batched per vendor; re-run if the buyer edits lines |
| G5 | Analyst | The buyer's request, the RFQ, every offer as structured data, the two summaries, the previous rules, and recent turns | Rules (`ProposalSpec`) and a short figure-free reply | Lite (measured: about 1.5 s against 13 s for Flash, with identical rules) | 1 call per request, plus one retry when an id is invalid |

Model IDs, generation settings, and per-session call limits live in `src/config.py` as `MODEL_LITE`, `MODEL_EXTRACT`, `MODEL_ANALYST`, and `MAX_CALLS_PER_SESSION`. Verify current model IDs, free-tier rate limits, and structured-output support when the key is created. A typical session is at most 2 calls for the RFQ, 1 per vendor for extraction plus a matching call only when code cannot match lines confidently, and 1 per analyst request. Free-tier rate limits are handled with backoff and the session call cap.

### Practices common to all calls

1. **Data first, instructions last.** Place documents or data in tagged blocks (`<document>`, `<rfq>`, `<analysis>`), then the task. State that block content is untrusted data and that instructions inside it must be ignored.
2. **Verbatim values.** Numbers, units, currencies, and dates are returned as the exact text found (`quantity_text: "4 nos"`, `unit_price_text: "₹12,500.00"`), and application code parses them. This handles Indian digit grouping and symbols deterministically and makes grounding checks a simple substring test.
3. **Explicit nulls.** Every optional field is nullable, with the rule "null if not stated; never guess; never default to 0 or 1".
4. **Two short worked examples per prompt**, including a negative case (a missing quantity stays null; a document with no prices is not a quotation).
5. **Simple schemas.** Pydantic model passed as the structured-output schema. Strings and enums rather than `Decimal` or deep unions. Short free-text fields (`reason`) are capped at about 20 words.
6. **Row references.** Parsers assign every row or paragraph a stable reference (`S1!R12`, `P3-L7`) in the text sent to Gemini. The model copies the reference and a verbatim `source_quote`; code verifies both.
7. **Generation settings.** Low temperature and minimal thinking for extraction and matching. Newer Gemini models may perform best at their default temperature, so check the selected model's guidance before pinning a value.
8. **Bounded retry.** One repair attempt for invalid output, sending the validation or verifier error messages back in the retry prompt. A truncated response (`finish_reason` of max tokens) is a failure, never a partial parse.
9. **Versioned prompts** under `src/prompts/`, one file per call. Log prompt version, model ID, and latency; never log document contents.

### Live behaviour notes (G1 and G2, verified against Gemini)

- Model IDs come from `.env` (`GEMINI_MODEL_LITE`, `GEMINI_MODEL_EXTRACT`), never from code. Check availability first: older families can be closed to new keys (the 2.5 models were, when this was built), so the API's model list is the source of truth. Gemini 3.x models are called with default temperature and minimal thinking.
- Calls use schema-constrained JSON validated with Pydantic. The SDK's own retries are disabled; the client retries a 5xx once and never retries a 429, which surfaces as a "busy, try again in a minute" message with the buyer's text kept.
- The client forces IPv4. On some networks the IPv6 route to Google hangs until the timeout, which looks like a frozen app.
- G2 runs in batches of 30 items. A 35-line messy list took 2 calls and about 12 seconds. A confident G2 pick is applied automatically only when its word-match score is within `MATCH_PICK_TOLERANCE` of the best candidate; otherwise it is shown first as a suggestion in the picker (an observed failure: "Anchor bolts" chosen for "hex bolts").
- Automated tests never reach the live API (`tests/conftest.py` blanks the key); live checks are run by hand with a hard call cap.

### G1 — RFQ parse

Purpose: split the request into distinct items and extract the buyer's own wording. It does not search or choose catalogue entries.

```python
class ParsedItem(BaseModel):
    original_text: str                 # verbatim slice of the buyer's input for this item
    item_phrase: str                   # the product name in the buyer's words, without quantity or unit
    search_terms: list[str]            # up to 3 alternative catalogue-style names, most likely first
    quantity_text: str | None          # verbatim, e.g. "4", "ten", "a dozen", "10-12"
    unit_text: str | None              # verbatim, e.g. "nos", "mtrs", "ltr"
    question: str | None               # one specific question if the item cannot be parsed

class ParseResult(BaseModel):
    input_class: Literal["procurement_request", "unrelated", "unintelligible"]
    items: list[ParsedItem]
    global_question: str | None
```

Prompt rules: one entry per distinct product; split compound requests ("2 gate valves and 3 globe valves" is two items); a shared quantity that applies to several products is not copied to each; `search_terms` generate singular and plural forms and common catalogue wording ("PT" becomes "pressure transmitter"); never infer a quantity or unit; return `input_class` first so unusable input costs nothing further.

### G2 — Catalogue resolve

Purpose: choose the best catalogue entry from a code-generated shortlist. The model cannot add entries.

The application builds the shortlist with RapidFuzz over `search_terms` against commodity titles and definitions (section 7). Items with one clear exact or near-exact winner are resolved by code and skip G2.

```python
class Resolution(BaseModel):
    item_index: int
    choice_code: str | None            # must be a code from that item's shortlist
    confidence: Literal["high", "medium", "low"]
    reason: str                        # at most 20 words
    alternatives: list[str]            # other plausible codes from the shortlist

class ResolveResult(BaseModel):
    resolutions: list[Resolution]
```

Prompt rules: choose only from the shortlist; prefer the most specific entry that the buyer's words fully support; return null when the shortlist does not clearly contain the product, rather than the nearest-sounding entry; list plausible alternatives when more than one fits.

Clarification is driven by the UI wherever possible: ambiguity between catalogue entries is a picker over `alternatives`, and a missing quantity or unit is an editable cell. Free-text clarification is reserved for input G1 could not parse, and re-runs G1 on the edited text.

### G3 — Quote extraction

Purpose: transcribe what the vendor wrote. It sees the document only, never the RFQ, so it cannot bend lines toward expected items.

```python
class ExtractedLine(BaseModel):
    row_ref: str
    source_quote: str                  # verbatim text of the row
    description_text: str
    quantity_text: str | None
    unit_text: str | None
    unit_price_text: str | None
    price_basis_text: str | None       # "per 100", "per kg", "each"
    line_total_text: str | None
    currency_text: str | None          # as written: "₹", "Rs", "USD"
    line_discount_text: str | None
    tax_text: str | None               # "GST 18%", "inclusive of tax"
    lead_time_text: str | None
    moq_text: str | None
    option_label: str | None           # "Option A", "Alternate", "Substitute"
    remarks: str | None

class Charge(BaseModel):
    kind: Literal["freight", "tax", "discount", "packing", "other"]
    scope: Literal["line", "quote"]
    text: str                          # verbatim
    row_ref: str | None

class ExtractedQuote(BaseModel):
    is_quotation: bool
    vendor_name_text: str | None
    quote_reference_text: str | None
    quote_date_text: str | None
    revision_text: str | None
    validity_text: str | None
    payment_terms_text: str | None
    delivery_terms_text: str | None
    stated_total_text: str | None
    lines: list[ExtractedLine]
    charges: list[Charge]
    warnings: list[str]
```

Input handling: CSV/TSV, Excel, and DOCX are sent as text tables with row references. Digital PDFs are sent as text with page and line references. Scanned PDFs and images are sent to Gemini natively with page references; their output is marked "read from image". Large tables are split into row-numbered chunks and the results merged; never send a table that would exceed the output limit in one call.

Prompt rules: transcribe only; total, subtotal, tax, and freight rows are charges rather than lines; cover letters and terms pages feed the quote-level fields; report every line including unpriced ones; set `is_quotation` to false when the document has no priced items.

### G4 — Quote-to-RFQ matching

Purpose: map extracted lines to RFQ items. Text in, text out; it is cheap to re-run when the buyer corrects a line.

Code goes first. For each line, RapidFuzz similarity against every RFQ item (catalogue title plus the buyer's original wording) and a numeric-token check (sizes and ratings in the RFQ wording must appear in the quoted description) run in `quote_matching.py`. A line with one clear winner and no disagreeing numbers is marked `matched` by code. G4 receives only the remaining lines: those with no clear winner, those with disagreeing numbers (so the differences can be explained), and those that appear to match several items. Clean quotes may need no G4 call at all.

```python
class LineMatch(BaseModel):
    line_id: str
    rfq_item_id: str | None
    status: Literal["matched", "possible", "no_match", "extra"]
    differences: list[str]             # visible differences: size, rating, material, make, quantity basis
    is_alternate: bool                 # vendor offers a substitute or alternative
    reason: str                        # at most 20 words

class MatchResult(BaseModel):
    matches: list[LineMatch]
```

Prompt rules: `matched` means the same product type with no visible difference; if the quoted description names a size, rating, material, or make that differs from the RFQ item's original wording, use `possible` and list the differences; `extra` is for real quoted products that are not on the RFQ; never choose an RFQ item because it is the only one left; one line maps to at most one RFQ item.

### G5 — Analyst (Purchase Proposal)

Purpose: turn the buyer's plain-language request into a Purchase Proposal. The model reads language; code does all arithmetic and optimisation.

**Division of work.** The model returns *rules* and a one to three sentence reply with no figures. Code validates the rules against real ids, finds the cheapest purchase that keeps them, computes every number in `Decimal`, checks the rules against the actual result, and writes the rule report itself. A rule that cannot be kept is dropped and reported as not met, with the reason, while the rest is still solved.

**Rules (`ProposalSpec`, all optional):** `allow_split`, `every_vendor_supplies`, `min_items_per_vendor`, `require_vendor_ids`, `leave_out_vendor_ids`, `max_vendors`, `pins` (item to vendor, optionally a quantity), `include_flagged`, `assume_rfq_unit`. The model also returns `unsupported` (the request needs something the quotations cannot give) or one `clarifying_question`. The objective is always the lowest total. The model refers to vendors and items by short aliases (V1, I3); code maps them back and rejects any alias it did not give.

**Context pack (built by code):** the RFQ with the buyer's wording and required quantities; each kept vendor with currency, tax basis, validity, payment, delivery, stated charges and open review points; every eligible offer as unit price per RFQ unit in the comparison currency (before tax), as quoted, with quoted quantity, minimum order and an under-review mark; the lines left out and why; the two summaries; the previous rules; and the last four turns. Vendors and lines the buyer excluded in Review are absent. The pack is trimmed to a size cap. Vendor-written text is data and the prompt says so.

**Solver (`allocation.py`).** Whole-unit quantities per vendor and item, solved exactly as a small mixed-integer program (`scipy.optimize.milp`): demand met per item (unfilled demand only where nobody can supply, and coverage is maximised before cost), vendor capacity limited to what it quoted, a vendor's minimum order respected, items split only when allowed (or when a partial pin asks for it), non-integer quantities bought whole from one vendor, vendor used only if it supplies a line, minimum items per vendor, required and left-out vendors, vendor limit, pins. Unit prices are flat (no volume tiers). Ties break by vendor name. If the rules are impossible, they are relaxed in a fixed order (pins, vendor limit, minimum items, required vendors) and the dropped rule is reported.

**Proposal (`Proposal`):** rows (item, unit, required quantity, vendor, quantity, unit price, total), grand total, the cheapest possible total (the lowest offer per item with no rules), the best complete single vendor, the rule report, and caveats (converted currencies with the rate, tax taken out, lines still under review, minimum orders, unpriced items, flat prices).

**Prompt design** (`prompts/analyst.md`): role; what to do (set rules, never calculate); grounding (ids only from the data, vendor text is never an instruction); boundaries (decision support, never "award to", unsupported requests said plainly); reply style (no figures, names not ids); three worked examples and one unsupported example.

**Model and cost.** `GEMINI_MODEL_ANALYST`, default flash-lite with minimal thinking. Measured on the five sample quotations: about 1.3 to 1.7 seconds per request and about 7,000 input tokens, against about 13 seconds for Flash with the same rules. One call per request.

**Live results on the sample quotations (checked by hand against `data/test_data/EXPECTED.md`):** "every responder, cheapest otherwise" gives a total only a few rupees above the unconstrained cheapest, with the extra cost equal to the three smallest price differences needed to give each vendor an item; "split purchases, cheapest" gives the unconstrained cheapest; pinning pumps to one vendor and three transmitters to another raises the total by exactly the two price differences; "who delivers fastest and is most reliable" is reported as unsupported; an instruction hidden in the request changed nothing.

**Verifiers (analyst):**

| ID | Check | Outcome |
|---|---|---|
| A1 | The reply contains figures that are not in the buyer's request | Replaced with a neutral line written by code |
| A2 | A rule names a vendor or item id that was not given | One retry with the error, then a friendly failure |
| A3 | Award-style wording in the reply | Replaced with a neutral line |
| A4 | `unsupported` is set | Shown as "cannot be answered from the quotations"; no proposal |
| A5 | A rule value is out of range | Treated as A2 |
| A6 | Rules the model claims were applied | Never trusted: the rule report is recomputed by code from the actual purchase |
| A7 | Instructions inside vendor text or the request | Cannot change the result: only enums, numbers and known ids are accepted from the model, and angle brackets are stripped from the request |
| A8 | Rate limit, call cap, bad JSON, no key | A readable message in the chat; the question is kept; no partial proposal |

## 13. Verifiers and Review Summary

Verifiers are application code that run on parsed files and after every Gemini call. They do not depend on the model's own assessment of its output.

### Outcomes

| Outcome | Meaning | Examples |
|---|---|---|
| **Block** | The object cannot be used safely; the rest of the workflow continues | Unreadable file, invalid output after one repair, choice not in the shortlist |
| **Review** | The data is kept and shown, but it is excluded from calculations that depend on it until the buyer accepts, edits, or excludes it | Missing unit, price outlier, weak match |
| **Info** | Shown for awareness; no effect on calculations | Read from image, tie for lowest price |

Only unusable or unsafe objects are blocked. Anything the buyer could reasonably judge, such as an unstated unit, is flagged for review rather than rejected. A flagged unit is never assumed: the line stays visible, is excluded from rankings, and the buyer can choose "use the RFQ unit", which is recorded in the summary.

### Review flags and the Review summary

```python
class ReviewFlag(BaseModel):
    flag_id: str
    code: str                          # e.g. "Q22"
    severity: Literal["block", "review", "info"]
    scope: Literal["rfq_item", "file", "vendor", "quote_line", "match", "analysis"]
    scope_id: str
    message: str                       # plain language for a procurement user
    resolution: Literal["accepted", "edited", "excluded"] | None = None
```

The **Review summary** is a panel shown in two places: above the RFQ table (Generate an RFQ) and at the top of the results (Evaluate Quotations), with a per-vendor view. It shows counts by severity, lists each flag with its message and a link to the affected row, and offers Accept, Edit, or Exclude where applicable. Entries never disappear: each starts as **Fix** (red, must be edited) or **Review** (orange, can be accepted), becomes **Reviewed** (green) when the buyer clicks Accept, and **Fixed** (mint green) when an edit in the table makes the problem go away. The state lives in `RFQ.review_log` and is recalculated after every edit. The panel is not shown as an empty placeholder: with no flags at all it shows a short "All clear" card. The analysis PDF includes the summary. State lives in `st.session_state`.

### RFQ verifiers

| ID | Check | Outcome |
|---|---|---|
| R1 | Input is empty, over the length limit, or mostly non-alphabetic (no model call) | Block |
| R2 | G1 response truncated, or schema-invalid after one repair | Block (draft preserved) |
| R3 | `input_class` is not `procurement_request` | Block, with guidance to describe items, quantities, and units |
| R4 | An item's `original_text` does not appear in the buyer's input | Review (item unverified) |
| R5 | `quantity_text` does not appear in the input | Review (quantity cleared) |
| R6 | Quantity is unparsable, a range, zero or negative, non-finite, or above the configured cap | Review (quantity blank; save blocked until set) |
| R7 | Fractional quantity on a discrete unit (Nos, Set, Pair, Kit, Box, Pack, Roll, Drum) | Review |
| R8 | `unit_text` cannot be mapped to a canonical unit | Review (unit blank) |
| R9 | No unit stated | Info (catalogue `default_unit` shown as a suggestion the buyer can change) |
| R10 | Stated unit differs from the catalogue `default_unit` | Info |
| R11 | G2 `choice_code` is not in that item's shortlist | Block for the item (treated as unmatched) |
| R12 | Best shortlist score is below threshold, or the margin over the next candidate is small | Review (picker shown; nothing auto-selected) |
| R13 | Two items resolve to the same catalogue entry | Review (possible duplicate) |
| R14 | Input has many separated segments but few parsed items | Review (items may have been merged) |
| R15 | Clarification turns exceed the limit, or the input is unchanged since the last call | Block further calls; buyer edits to continue |
| R16 | Session call limit reached | Block |
| R17 | Unmatched items at save time | Review (explicit acknowledgement required) |
| R18 | Input contains instruction-like text (for example, "ignore previous") | Info |
| R19 | RFQ name has unsafe characters or duplicates an existing name | Info (sanitized; suffix added) |

### Quote file and extraction verifiers

| ID | Check | Outcome |
|---|---|---|
| Q1 | Extension unsupported, or the real file type does not match the extension | Block (file) |
| Q2 | File is empty, corrupt, encrypted, or over the size, page, or row limits | Block (file) |
| Q3 | Duplicate file (content hash) | Block (duplicate); Info |
| Q4 | Hidden sheets, rows, or columns present | Review (marked as hidden) |
| Q5 | Excel formula cells without a cached value | Review |
| Q6 | PDF has little or no text layer and is read from an image | Review (lower-confidence extraction) |
| Q7 | G3 response truncated or schema-invalid after one repair | Block (file); other files continue |
| Q8 | `is_quotation` is false, or no priced lines found | Block (file, "no quotation found") |
| Q9 | `row_ref` does not exist, or `source_quote` is not in that row's parsed text | Review (evidence unverified; line excluded until accepted) |
| Q10 | A price, quantity, or total text is not present in the source row after normalization (symbols, commas, Indian grouping) | Review |
| Q11 | A price text is unparsable | Review (price stays missing, never 0) |
| Q12 | Price is zero | Review ("free or missing?"; excluded) |
| Q13 | Far fewer lines extracted than rows in the parsed table | Review (file: possible missed lines) |
| Q14 | Total, subtotal, tax, or freight rows extracted as items | Info (moved to charges) |
| Q15 | Identical duplicate lines | Review (duplicate suggested for removal) |
| Q16 | Quantity × unit price differs from the stated line total beyond tolerance | Review |
| Q17 | Sum of lines differs from the stated subtotal or total | Review (vendor) |
| Q18 | Currency missing, ambiguous (`$`, `Rs`), or mixed within a quote | Review (buyer confirms currency) |
| Q19 | Unit not stated | Review (excluded from ranking unless the buyer applies the RFQ unit) |
| Q20 | Unit not canonical or not convertible to the RFQ unit | Review (incomparable) |
| Q21 | A price basis such as "per 100" is present but not parsed | Review |
| Q22 | Normalized price differs from other vendors' prices for the same item by more than 10× or less than 0.1× of the median (two or more vendors) | Review (possible unit or decimal error) |
| Q23 | Tax inclusive or exclusive status is unclear | Review (vendor) |
| Q24 | Validity date expired or unparsable | Review |
| Q25 | Vendor name missing or not found in the document | Review (buyer must enter it before comparison) |
| Q26 | Same vendor appears in several files or revisions | Review (buyer selects one) |
| Q27 | Instruction-like text in the document | Info |

### Matching verifiers

| ID | Check | Outcome |
|---|---|---|
| M1 | `rfq_item_id` does not exist in the RFQ | Block (line treated as unmatched) |
| M2 | Status `matched` but text similarity is below threshold | Downgraded to `possible` (Review) |
| M3 | Differences listed, or the RFQ item's numeric tokens (sizes, ratings) are missing from the quoted description | Review (possible technical mismatch) |
| M4 | Several lines map to one RFQ item | Review (treated as options; buyer picks one) |
| M5 | One line maps to several RFQ items | Review |
| M6 | RFQ item has no matched line from a vendor | Info (coverage gap) |
| M7 | Quoted quantity differs from the RFQ quantity | Review (comparison uses RFQ quantity; deviation shown) |
| M8 | Minimum order quantity exceeds the RFQ quantity | Review |
| M9 | Line is marked as an alternate or substitute | Review |

### Calculation verifiers

| ID | Check | Outcome |
|---|---|---|
| C1 | Internal reconciliation: eligible lines plus excluded lines equals all lines | Assertion (failure is a bug) |
| C2 | Exchange rate missing | Review (excluded from converted ranking) |
| C3 | Exchange rate not positive, undated, or outside a sanity band | Block conversion; manual rate override allowed |
| C4 | Tie for the lowest price | Info (all tied vendors listed) |
| C5 | No eligible price for an RFQ item | Review (hybrid incomplete) |
| C6 | Vendor does not cover all items | Info (single-vendor scenario ineligible, with reason) |

### Analyst verifiers

See the table under G5 in section 12.

## 14. User Interface and Design System

Use a neutral enterprise visual language without hard-coding an external brand identity.

- **Canvas:** soft off-white/light neutral.
- **Surfaces:** white cards/panels with subtle borders.
- **Primary text:** deep navy or charcoal.
- **Primary action:** restrained teal/blue-green.
- **Secondary accent:** muted blue for informational elements.
- **Status colors:** accessible green, amber, and red, always paired with text/icons so meaning does not depend on color alone.
- **Typography:** clean sans-serif hierarchy; readable labels; compact data tables; clear headings.
- **Components:** consistent spacing, restrained radius, compact status badges, visible focus states.

Top-level navigation: **Generate an RFQ**, **Manage My RFQs**, **Evaluate Quotations**, shown as pill tabs. Navigation is app-controlled (a keyed segmented control, `app/ui/nav.py`) rather than `st.tabs`, so buttons in the flow can switch screens: after saving, **View in Manage RFQs**; in Manage, **Select for evaluation** selects the RFQ and opens Evaluate. Only the active screen renders. Clicking the active pill keeps the current screen. Each screen should make the current workflow state visible and provide clear empty, loading, incomplete, success, and error states.

Row order in the RFQ table is decided once, when the RFQ is built (review lines first), and stored as `display_order`. Editing a line never moves it, so the buyer can keep working down the list.

**RFQ builder:** before a request, a centred chat-style box (Enter sends). After it, a split layout: the request and a box for a new request on the left, the Review summary (or an "All clear" card) on the right, and **Your RFQ** full width below. Unclear requests get a guidance card with an example and a "Use this example" button. While the RFQ is built, an animated progress card shows the real stages (reading, matching, choosing, preparing).

**Your RFQ table:** the heading carries the line count and review count, the RFQ name, and **Save RFQ**, which stays disabled and says why ("Resolve 12 to save") until every flag is resolved or accepted; after saving it becomes **Download PDF** and **New RFQ**. Lines that need review are listed first and confirmed lines last. All editing (quantity, unit, catalogue item, remove) is in the table; the Review summary lists every flagged line with its state and offers Accept where acceptance is allowed. Choosing a catalogue item confirms the line, closes the picker, and shows a short confirmation; the picker lists the current item and offers only the other close matches. While an RFQ is being built, the screen switches to the split layout: the request stays visible and read-only in the input box's place on the left, and a progress card the size of the Review summary shows the real stages on the right. Rows are colour-coded: red (must fix), amber (needs a decision), blue (a suggestion was applied: close match or suggested unit), green (confirmed), and the specific field in error gets a red outline (a suggested unit gets a dashed teal one). The catalogue picker is a wide popover with a large search box that opens on suggested close matches for the line's own wording.

The shell is a slim top bar (logo and name on the left) with the three tabs directly beneath it.

**Manage RFQs:** session-only list, view/download/select actions, and empty state.

**Evaluate Quotations:** RFQ selector, multi-file upload, per-file status/recovery, vendor/revision confirmation, extraction/mapping review, Review summary (overall and per vendor), the Compare step (Purchase Proposal, lowest offer per item, vendor totals, lines left out, exchange rates) with the analyst chat, and no download.

**Analyst panel:** chat input, starter-question chips, assumption chips (removable), answers with inline tables and charts, a **How this was calculated** expander, and export buttons.

## 15. Failure Handling and Recovery

Handle failures at the smallest relevant scope. Preserve valid work when one item or file fails.

| Scenario | Expected behavior |
|---|---|
| Empty RFQ input | Show guidance; do not call Gemini. |
| Gibberish/unrelated input | Explain no usable request was found; ask for a revised description. |
| Missing quantity | Leave blank, flag, and block finalization until supplied. |
| Missing/unclear unit | Show the catalogue default as a suggestion; flag for review; do not infer silently. |
| No catalogue match | Keep original text, flag review, and do not fabricate a record. |
| Multiple catalogue candidates | Show candidates and request selection/clarification. |
| Gemini timeout/rate limit | Preserve draft; show retryable error; use bounded retry/backoff. |
| Invalid Gemini JSON | Validate, attempt one bounded repair, then show recoverable failure. |
| Missing/corrupt catalogue | Disable dependent RFQ operations and show actionable error. |
| Unsupported upload | Reject only that file and list supported formats. |
| Non-quotation document | Mark unrecognized/rejected with reason; allow replacement/removal. |
| Empty/corrupt/encrypted/oversized file | Reject or request replacement; continue other files. |
| Scanned PDF | Send to Gemini natively within the page limit; mark as read from an image. |
| Legacy `.xls`/`.doc`, image, or other unsupported file | Reject only that file; ask for `.xlsx`/`.docx`; list supported formats. |
| Analyst tool error or round limit | Retry once with the error; then show results so far and a clear message. |
| Free-tier rate limit | Back off and retry within bounds; preserve state; show a retry message. |
| Unclear vendor identity | Require buyer confirmation before comparison. |
| Multiple revisions per vendor | Require selection of one version. |
| Ambiguous quote-line mapping | Flag for review and exclude until resolved. |
| Missing price/quantity/unit/currency | Flag affected line and exclude from calculations requiring it. |
| Currency rate unavailable | Preserve source value; exclude from INR comparison; show warning. |
| Incomplete vendor coverage | Mark scenario incomplete/ineligible; do not imply full coverage. |
| No eligible prices | Explain why comparison is unavailable; do not fabricate ranking. |
| PDF generation failure | Preserve validated state and offer retry. |
| Session reset/expiry | Treat as a fresh session; do not claim persistence or recovery. |

For recoverable failures, retain the maximum safe prior state and provide a clear next action.

## 16. Security, Privacy, and Resource Controls

### Uploaded content and model context

- Treat uploaded files and extracted text as untrusted input; ignore embedded instructions that attempt to alter behavior or reveal secrets.
- Do not send API keys, environment variables, internal secrets, or unrelated session data to Gemini.
- Send only the selected RFQ, relevant catalogue candidates, and minimum document content needed for the task.
- Avoid logging full quotations by default.

### Resource controls

- Enforce extension/type checks, maximum file sizes, and limits on PDF pages, spreadsheet rows/sheets, extracted characters, and model input length.
- Set explicit API timeouts, bounded retries, and per-session upload limits.
- Prevent unbounded loops or repeat calls on unchanged invalid input; clean up temporary files where feasible.
- Sanitize filenames; never use user-supplied filenames directly as filesystem paths.

### Application safety and privacy

- Keep credentials server-side; pin dependencies; do not commit secrets.
- Do not execute model-generated code, shell commands, or arbitrary filesystem operations.
- The analyst's model call returns only rules made of enums, numbers and ids we supplied; code validates them and does all calculation. The model has no tools, no network, file, or code-execution access, and cannot initiate external side effects.
- The MVP does not intentionally persist RFQs or quotes to a database. Hosting and API providers may have separate logging, retention, and processing terms; review them before using confidential procurement documents. Prefer synthetic/demo data for public demos unless real-data handling is approved.

## 17. Testing

### Unit tests

Test catalogue loading/normalization/search and ambiguity; input validation and state transitions; Pydantic validation; malformed model output; every verifier in section 13; file validation and parsers; unit aliases and conversions; currency conversion; deterministic item pricing, sourcing scenarios, and the maximum-vendor search; the allocation solver (against exhaustive search on small random cases), rule validation, and the analyst's reply and failure handling; the RFQ PDF contents; filename sanitization; and temporary-file cleanup.

### Integration tests

Test RFQ input → Gemini → schema validation → catalogue search → clarification/edit → save; RFQ selection → multi-file upload → parsing → extraction → confirmation → comparison; the analyst request-to-proposal flow (with a scripted fake Gemini); the RFQ PDF export; and partial failure where an invalid file does not block valid files. Use mocked Gemini/rate responses for repeatable CI. Keep live API smoke tests separate and opt-in.

### Manual testing

There is no evaluation suite and no scheduled live-model testing; the free-tier API is used only as the app is used. Runtime protection comes from the verifiers and the Review summary. After the MVP runs, synthetic sample data is created and stored in `data/` for manual testing: a sample RFQ and several vendor quotations covering alternative units, charges, partial coverage, mixed currencies, a messy layout, and an emailed quotation saved as a `.docx`.

### Definition of done

- All three tabs work end-to-end.
- RFQs can be extracted, catalogue-searched, clarified, edited, saved in-session, and exported.
- Missing/invalid quantities and unresolved ambiguity cannot pass silently.
- Multiple supported quote files process independently, with buyer confirmation for vendor/revision uncertainty.
- Comparisons are deterministic and derived from validated data.
- Currency rates include source/timestamp; failed conversions are safely excluded.
- Analysis distinguishes eligible comparisons, exclusions, and indicative scenarios.
- The RFQ PDF is downloadable.
- The analyst builds a Purchase Proposal from a plain-language request (split purchases, every vendor included, vendor limits, pinned items) with figures that all come from code.
- Core unit and integration tests pass, including every verifier.
- No API keys or confidential test documents are committed.

## 18. Deployment

### Local setup

1. Install the supported Python version and create a virtual environment.
2. Install pinned dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env` and set the Gemini API key locally.
4. The trimmed catalogue ships in `data/unspsc_catalogue.csv`; no setup is needed.
5. Run the Streamlit application.
6. Run tests with pytest.

The README should document setup, run/test commands, configuration, and session-only data behavior.

### Streamlit Community Cloud

- Connect the GitHub repository to Streamlit Community Cloud.
- Configure the Gemini key with Streamlit secrets.
- Verify model availability, quota, and provider limits.
- Confirm the catalogue is included and loads correctly.
- Apply reasonable upload limits/timeouts and run smoke tests for each tab.
- Use synthetic/demo documents unless real-document handling is approved.
- Optionally make the app private (viewers sign in and must be invited) to limit exposure of the Gemini key's quota.
- Session data is lost on refresh by design; this is documented in the README.
- Set `MAX_CALLS_PER_SESSION` in the secrets (25 for the public demo) so one visitor cannot use up the key's quota.

This is a basic demo deployment, not an SLA-backed production service or durable storage solution.

### Pre-demo checks

Confirm app availability, API key/model quota, catalogue load/version, one RFQ flow, one quote-analysis flow, the RFQ PDF download, session behavior, and absence of confidential content in logs/repository.

## 19. Implementation Phases

| Phase | Focus | Exit criteria |
|---|---|---|
| 1. Foundation | Repository, config, schemas, session state, Streamlit shell | App runs locally; configuration is externalized; schema/state tests pass. |
| 2. Catalogue + RFQ | Catalogue search, units, G1/G2, editable table with Review summary, RFQ PDF | Buyer can complete/save/export RFQ; unmatched items are safely flagged. |
| 3. RFQ management | Session list, view/download/select for evaluation | Saved RFQs work in-session; empty state and lifecycle notice work. |
| 4. Ingestion + extraction | Parsers, G3 extraction, code-first matching with G4, Review summary, vendor/revision review | Multiple quotes process independently; invalid files do not block valid ones. |
| 5. Comparison + analyst (final build phase) | Deterministic pricing and currency, the Compare step, the analyst and its allocation solver | Results are reproducible, evidence-backed, and qualified; the analyst's rules are shown and checked by code. No analysis download. |
| 6. Hardening + deployment | Security/resource controls, verifier tests, rate-limit handling, deployment | Demo-ready deployment; limitations documented; no secrets committed. |

## 20. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Catalogue descriptions are inconsistent/incomplete | Normalize for retrieval; preserve original; expose candidates and buyer review. |
| Unsupported LLM inference | Explicit prompts, schema validation, evidence, uncertainty, deterministic verification. |
| Similar descriptions cause false matches | Staged search, configurable thresholds, review states, and manual confirmation. |
| Vendor layouts vary | Format-specific parsers, native Gemini reading of scanned PDFs, per-line review. |
| Unit/spec differences make prices incomparable | Compare only eligible lines; require trusted conversions; flag deviations. |
| Exchange rate missing/stale | Record source/time; preserve original; exclude unconverted amounts from target ranking. |
| API limits/model availability change | Configurable model; quota-error handling; verify before deployment; no free-tier assumptions. |
| Session data is lost | Make session-only behavior explicit; do not imply persistence. |
| The analyst misreads a request, or tries to compute | One structured call that can only return rules (enums, bounded numbers, known ids); an exact solver and every figure in code; the rules it understood are shown and re-checked against the result; a per-session call cap. |
| Free-tier rate limits | Backoff, call caps, batching, and code-first matching in G2 and G4 to reduce calls. |
| Prompt injection or malicious files | Treat content as data; constrain context; validate files; prevent model-controlled actions. |
| Demo mistaken for production-ready | Label prototype assumptions; exclude unimplemented security, persistence, integrations, and approvals from claims. |

## 21. Repository Deliverables

- Runnable Streamlit application with the three tabs.
- Typed RFQ, quotation, analysis, and review-flag schemas.
- Trimmed catalogue (`data/unspsc_catalogue.csv`), search module, and units module.
- Centralized Gemini client and versioned prompts.
- Document parsers, with native Gemini reading for scanned PDFs.
- Deterministic comparison and currency-normalization engine.
- Verifiers and the Review summary.
- Analyst (rules from the model, allocation solver and every figure in code).
- RFQ PDF generation.
- Unit and integration tests (verifiers, tools, engine, units).
- `.env.example`, dependency manifest, `.gitignore`, and setup/deployment README.
- This implementation plan maintained alongside the PRD.

## 22. Acceptance Checklist

- [ ] Three tabs are present and clearly named.
- [ ] Natural-language RFQ input is parsed into distinct items.
- [ ] Only explicitly stated quantities and units are extracted.
- [ ] Catalogue results are grounded in the bundled catalogue.
- [ ] Missing/ambiguous details trigger clarification or buyer review.
- [ ] Unmatched items are retained without fabricated identifiers.
- [ ] Missing/invalid quantities prevent finalization.
- [ ] RFQs can be edited, saved for the session, viewed, and downloaded as PDF.
- [ ] Session-only behavior is accurately documented.
- [ ] Supported quote formats are parsed or rejected with actionable messages.
- [ ] File failures are isolated; valid uploads continue.
- [ ] Vendor identity and quote revision can be confirmed.
- [ ] Quote extraction is schema-validated and evidence-backed.
- [ ] Price arithmetic and rankings are deterministic application code.
- [ ] Taxes, freight, and discounts are shown beside prices and never silently included or assumed zero; the basis is unit price × RFQ quantity, excluding tax.
- [ ] Currency conversions include rate source/timestamp; failed conversions are never guessed.
- [ ] Comparisons distinguish eligible, excluded, incomplete, and uncertain data.
- [ ] Single-vendor and hybrid scenarios are labeled indicative decision support.
- [ ] The analyst sets rules only, and every figure in a proposal originates in code.
- [ ] What-if questions (exclude a vendor, limit vendor count) work and show their assumptions.
- [ ] The Review summary lists every flag; nothing is rejected for an unstated unit.
- [ ] Suggested units are visibly marked and never applied silently.
- [ ] The RFQ PDF is downloadable.
- [ ] Secrets are not committed or exposed to the client.
- [ ] Tests cover the verifiers, the allocation solver, the analyst service, the comparison engine, and unit conversion.
- [ ] Deployment instructions and MVP limitations are documented.

## 23. Deployment Record

The app is deployed on Streamlit Community Cloud from the `main` branch (`app/main.py`, Python 3.12), with the Gemini key, the three model names and `MAX_CALLS_PER_SESSION` held in the platform's secrets. It is public; the per-session call cap limits what one visitor can use.

Verified on the deployed app with the five sample quotations: the RFQ is generated and saved; five quotations are read in about 20 seconds (two at a time); the Review step shows the planted cases; Compare shows the lowest offers and vendor totals with the exchange-rate lookup working; the analyst returns a Purchase Proposal in about 3 seconds; and the session cap disables the analyst input once reached. A free app can sleep when idle, so the first visit may take a few seconds to wake it.
