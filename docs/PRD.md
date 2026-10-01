# Product Requirements Document

## 1. Problem Statement

Procurement teams at refineries and process-manufacturing plants routinely source maintenance, repair, and operations (MRO) materials and equipment. A request may begin as an informal note from a maintenance, electrical, or instrumentation team, but procurement must turn it into a usable request for quotation (RFQ), coordinate vendor responses, and evaluate quotations before a purchasing decision can be made.

Today, this work is often split across emails, spreadsheets, PDFs, Word documents, and manual checks. A procurement manager may spend several days clarifying item descriptions and specifications, preparing an RFQ, collecting vendor responses, reconciling different item names and units, and comparing prices and terms. Quotations frequently arrive in different layouts and levels of detail, making it difficult to establish whether vendors are quoting the same item, quantity, specification, or commercial basis.

This fragmented process creates avoidable effort and procurement risk:

- **Manual RFQ preparation:** translating loosely worded requirements into consistent line items, quantities, units, and specifications takes time and may require repeated clarification with requesters.
- **Inconsistent item descriptions:** the same or similar item may be described differently by the requester, catalogue, and vendors, complicating item matching and comparison.
- **Unstructured vendor responses:** quotation information is spread across documents and tables, requiring manual extraction and consolidation.
- **Non-comparable bids:** differences in units, quoted quantities, currency, discounts, taxes, freight, delivery conditions, or technical details can make headline prices misleading.
- **Limited traceability:** manual comparisons can make it difficult to trace an extracted value or matching decision back to the vendor's quotation.

The MVP will provide a single workflow to create a structured RFQ from a natural-language request, save and retrieve RFQs within the session, evaluate uploaded vendor quotations against a selected RFQ, and let the buyer ask questions about the comparison in plain language. It will reduce repetitive preparation and comparison work while keeping the procurement manager in control.

The product is intended to make the comparison process **faster, more consistent, and more transparent**—not to replace technical validation or make an autonomous purchasing decision. Missing information, uncertain matches, and material deviations must be visible to the user rather than silently inferred or treated as confirmed facts.

## 2. Target User

### Primary persona: MRO Procurement Manager

For the MVP, the target user is a **Procurement Manager or sourcing professional at an Indian refinery or process-manufacturing plant**, responsible for sourcing MRO materials, spares, and equipment used by plant maintenance and operations teams.

Illustrative Indian industry examples include **Indian Oil Corporation Limited** and **Reliance Industries Limited**, both listed among India's refinery operators by the Government of India's Petroleum Planning & Analysis Cell. These are examples of the target industry, not assumed customers or design partners: [PPAC — Location of Refineries](https://ppac.gov.in/infrastructure/location-of-refineries).

**Responsibilities**

- Receive purchase requirements from maintenance, electrical, instrumentation, and operations teams.
- Clarify item identity, quantity, units, and relevant technical requirements.
- Prepare RFQs and coordinate quotation collection from vendors.
- Review vendor responses for item coverage, pricing, technical alignment, and commercial terms.
- Compare offers and prepare an evidence-based view for internal review and purchasing decisions.

**Goals and needs**

- Reduce the time spent converting informal requests into structured RFQs.
- Find and select valid items from the available item catalogue.
- Identify missing or ambiguous requirements before issuing an RFQ.
- Consolidate vendor quotations received in different file formats and layouts.
- Compare prices on a consistent basis and quickly identify gaps, deviations, and potential cost savings.
- Understand how the system reached a match or calculation and retain final decision authority.

**Pain points**

- Repeated clarification between procurement and technical requesters.
- Manual searching and mapping of item descriptions.
- Re-keying quotation data into spreadsheets.
- Difficulty comparing quotes that differ in structure, units, quantities, or commercial terms.
- Risk of overlooking missing items, exceptions, or assumptions in a manual evaluation.

### Secondary stakeholder: Technical requester / reviewer

A maintenance, electrical, instrumentation, or operations engineer may provide the initial requirement or validate technical details. In the MVP, this stakeholder is represented through the procurement manager's supplied information and clarifications; a separate engineering workflow or approval role is not required.

## 3. User Journeys

The MVP is organized into three tabs: **Generate an RFQ**, **Manage My RFQs**, and **Evaluate Quotations**. The primary workflow is to create an RFQ, retrieve it within the same session, and use it as the baseline for quotation evaluation. Buttons in the flow move between the tabs (for example, after saving an RFQ, or when selecting an RFQ for evaluation). The MVP is session-only: there is no database or login, and refreshing the browser clears RFQs, uploads, and analysis (see section 4).

### 3.1 Generate an RFQ

**Objective:** Enable the procurement manager to describe a purchasing requirement in natural language, resolve any missing or ambiguous information, review structured line items (item, quantity, unit), and save and download an RFQ.

#### Journey

1. **Enter the request**
   - The user opens the Generate an RFQ tab and enters a natural-language request describing one or more required items.
   - The request may include item descriptions, quantities, units, and known specifications. The user submits the request.
   - A loading state is shown while the system interprets the request and searches the item catalogue.

2. **Parse and identify requested items**
   - AI interprets the request and splits it into distinct items, each with the buyer's own wording, a quantity, and a unit where stated. Only stated values are extracted.
   - The system searches the item catalogue (a trimmed UNSPSC commodity list for refinery and process-plant MRO; the commodity title is the item name; see section 4) and shortlists candidates. A clear match is selected by the system; when the match is not clear, AI chooses among the shortlisted candidates only. It must not create catalogue records.
   - The buyer's original wording is kept alongside the selected catalogue item so the mapping can be reviewed.

3. **Resolve anything missing or ambiguous**
   - Ambiguous items show a picker of the candidate catalogue entries. Missing or unusable quantities and units are shown as highlighted cells to fill in. Free-text clarification is used only when the request itself cannot be understood.
   - The system must not silently select an uncertain item, invent a quantity, or present an unresolved interpretation as confirmed. A unit that is not stated is shown as a suggestion taken from the catalogue and is clearly marked as suggested.
   - Items that cannot be matched stay visible with their original wording, flagged for review, and the buyer must acknowledge them before saving.

4. **Review the structured RFQ table**
   - Once the items are sufficiently resolved, the system displays an editable table with three columns: **Item**, **Quantity**, and **Unit**.
   - The Item cell shows the selected catalogue item; its UNSPSC identifier may be shown as supporting information without adding more primary table columns.
   - Selecting Edit on the Item field opens a searchable catalogue picker populated from the same catalogue. Quantity and unit are editable, and rows can be removed.
   - A **Review summary** beside the request lists everything that needs attention (unmatched items, missing quantities, unrecognised units, possible duplicates). Each entry changes state as the buyer works: Fix or Review while open, Reviewed once the buyer accepts it, and Fixed once an edit in the table resolves it; entries stay listed so progress is visible. Lines needing review are listed first in the table and highlighted, and the Save button states how many items remain.
   - The table must distinguish an absent value from a numeric zero, must require a positive quantity on every line before saving, and must not silently overwrite the user's input.
   - Units come from a small standard list (see section 4).

5. **Name, save, and download the RFQ**
   - The user can provide an RFQ name before saving. By default, the name is generated as `RFQ-YYYY-MM-DD`, using the current date; the user may edit the name.
   - The system assigns an RFQ identifier and saves the reviewed line items and associated RFQ details so the RFQ appears in Manage My RFQs.
   - The user can download the RFQ as a PDF. For the MVP, the PDF uses static mock company details and headers, along with the RFQ identifier, user-provided or default name, creation date, and the reviewed item table.
   - The PDF must reflect the saved, user-reviewed RFQ rather than an earlier unreviewed AI output.

**Expected outcome:** A saved, downloadable RFQ containing a user-reviewed list of catalogue items, quantities, and units, with every unresolved point either fixed or explicitly acknowledged before finalization.

### 3.2 Manage My RFQs

**Objective:** Give the procurement manager a simple place to find RFQs saved in the current session and select one as the basis for quotation evaluation.

#### Journey

1. **View saved RFQs**
   - The user opens Manage My RFQs and sees previously saved RFQs.
   - Each entry displays, at minimum, the RFQ name or identifier, creation date, and item count.
   - An empty state is shown when no RFQs have been saved.

2. **Inspect and retrieve an RFQ**
   - The user can open a saved RFQ to review its line items and details.
   - The user can download the RFQ PDF again.

3. **Select an RFQ for evaluation**
   - The user can select a saved RFQ and proceed to Evaluate Quotations.
   - The selected RFQ becomes the comparison baseline for the vendor quotations uploaded in that evaluation.

**MVP boundary:** This tab supports listing, viewing, downloading, and selecting saved RFQs. Editing, deleting, duplicating, approval workflows, RFQ distribution, and lifecycle/status management are not required for the MVP.

**Expected outcome:** The user can retrieve an existing RFQ and carry its reviewed item requirements into quotation evaluation without re-entering them.

### 3.3 Evaluate Quotations

**Objective:** Enable the procurement manager to upload vendor quotations for a selected RFQ, receive a transparent item-level and vendor-level comparison with an indicative lowest-cost multi-vendor combination, and explore it by asking questions in plain language.

#### Journey

Evaluate Quotations is presented as guided steps (Select the RFQ, Upload, Review, Compare, Ask the analyst); a step unlocks once the one before it is complete.

1. **Select the RFQ**
   - The user opens Evaluate Quotations and chooses one of the saved RFQs.
   - The system displays the selected RFQ's item list and makes it the baseline for matching, coverage checks, and comparison.
   - The user proceeds to upload vendor quotations for that RFQ.

2. **Upload vendor quotations**
   - The uploader accepts **CSV, TSV, Excel (`.xlsx`), PDF, and Word (`.docx`)** files. An emailed quotation can be uploaded as a `.docx`. Older `.xls` and `.doc` files, images, and other formats are rejected with a message to save them as `.xlsx` or `.docx`.
   - The user may upload quotations from multiple vendors. Where a vendor submits supporting files, the files can be associated with that vendor's quotation.
   - The system extracts vendor identity where available. If identity is missing or unclear, the user can enter or correct the vendor name before comparison. If several files come from one vendor, the user chooses which to use.
   - The system uses document parsing together with AI inference to interpret tables, line items, and surrounding quotation context. Extraction from scanned or image-based PDF pages may be uncertain and must be flagged for review rather than treated as verified.

3. **Extract and structure quotation information**
   - AI processes each quotation and produces structured vendor and line-item data for comparison against the selected RFQ.
   - Where present, relevant fields include vendor name, quote reference and date, quoted item description, quoted quantity and unit, unit price, currency, discounts, taxes, freight or other charges, delivery details, technical specifications, quote validity, and commercial terms.
   - The system preserves the source document and enough page, sheet, row, table, or text context to let the user inspect the origin of extracted values where technically available.
   - Missing fields remain missing; they must not be converted to zero or filled with invented values.

4. **Match vendor lines to RFQ items**
   - The system compares each vendor's quoted line items with the selected RFQ items using item descriptions and available contextual or technical attributes. Clear matches are made by the system; AI helps only with lines that are not clear.
   - It identifies matched, potentially matched, unmatched, additional, and unquoted RFQ items.
   - A broad catalogue-category match alone must not be presented as proof of technical equivalence.
   - Ambiguous mappings, low-confidence extraction, and potential technical mismatches are clearly flagged for buyer review. The system must retain the vendor's original description alongside the proposed RFQ match.
   - A quotation with partial coverage may still be evaluated for the items it quotes, but it must not be presented as a complete response.

5. **Normalize and validate comparable values**
   - The system compares like with like wherever the available data allows it, taking account of quoted quantities, units, currencies, discounts, taxes, freight, and other explicitly stated charges.
   - Unit conversions may be applied only for weight, length, and volume units with exact conversion factors. Differences in count units (for example a box quoted against numbers of pieces) are not converted and are flagged as not comparable. A price quoted per 100 or per 1000 is normalized to a unit price. Quantity differences and deviations from the RFQ remain visible.
   - Currency conversion requires an explicit, visible conversion basis, including the rate and its source or date when available. If no defensible conversion basis is available, retain the original currency and mark the offers as not directly comparable.
   - The comparison basis is unit price multiplied by the RFQ quantity, excluding tax. Taxes, freight, packing, and discounts are extracted and shown beside the price rather than added in. A quotation whose prices include tax is flagged. Ambiguous or missing commercial terms must be flagged and must not be silently assumed to be zero or equivalent.
   - Calculations such as line totals, comparable totals, and vendor allocations must be reproducible and based on validated structured data. AI may interpret documents and explain results, but must not invent or independently guess numeric values.

6. **Review the quotation comparison**
   - The system provides an item-by-item comparison showing the RFQ requirement and each vendor's relevant quoted value, price, and match or exception status.
   - It summarizes quotation coverage: which RFQ items each vendor quoted, which items are missing, and which additional or unmatched items require attention.
   - A **Review summary** lists every flagged item across all quotations (missing or unclear units, unusually high or low prices, weak matches, currency questions, and similar). Nothing is silently rejected: the buyer can accept, correct, or exclude each flagged item, and flagged lines stay out of rankings until the buyer decides.
   - It identifies the lowest comparable offer for each RFQ item and the lowest-total single-vendor quotation where the bids cover a comparable scope. Any limitations in coverage or comparability must be shown next to the result.
   - The user can inspect supporting quotation evidence and the reasons for a match, exception, exclusion, or calculation wherever available.

7. **Compare the quotations**
   - The Compare step shows two calculated summaries. **Lowest offer for each item** gives the cheapest single vendor for each RFQ item (one vendor fulfilling the whole item). **Vendor totals** gives what each vendor's quotation comes to for the whole RFQ and whether it covers every item.
   - Everything is calculated by the application on the same basis: unit price × RFQ quantity, before tax, in one currency. Lines that cannot be compared (no price, a unit that cannot be converted, an open review point, a missing exchange rate) are listed with the reason, never silently counted.
   - Exchange rates come from a lightweight lookup with the rate, source, and date shown, and the buyer can enter a rate. Without a rate, foreign-currency prices are left out of the ranking and the page says so.

8. **Ask the analyst for a Purchase Proposal**
   - Beside the summaries is a chat where the buyer describes the purchase they want in plain language, for example "make me a purchase summary allowing split purchases so the total is cheapest" or "I want a purchase relationship with every responder, take the cheapest options otherwise".
   - The result is a **Purchase Proposal** shown above the summaries: a quote-style table with the item, the required quantity, the vendor, the quantity bought, the unit price, and the total for each line, and a grand total. With split purchases allowed, the same item can be bought from several vendors, and the quantities add up to what the RFQ requires.
   - The AI reads the request and the quotations and turns the request into rules (split allowed, every vendor supplies at least one item, vendors left out, a limit on the number of vendors, an item fixed to a vendor, whether lines still under review are used). The application then finds the cheapest purchase that keeps the rules and calculates every figure. The AI never calculates, and the rules it understood are shown so a misreading is visible. If the rules cannot all be met, the proposal says which could not be kept and why.
   - Vendors and lines the buyer excluded in Review are left out. A follow-up request ("now at most three vendors") updates the previous rules. Each proposal shows how far it is above the cheapest possible total (the cost of the rules) and how it compares with the best single vendor.
   - When a request asks for something the quotations cannot answer (delivery speed, supplier reputation), the analyst says so. It presents a proposal for the buyer's consideration and never issues an award or purchase decision.

9. **Make the procurement decision**
   - The procurement manager reviews the item matches, quotation coverage, price comparisons, exceptions, and the proposal.
   - The user retains responsibility for validating technical suitability, resolving commercial ambiguities, and making the final sourcing or award decision.
   - The MVP ends with the comparison and proposal available for review on screen. It does not send RFQs to vendors, negotiate, create purchase orders, execute awards, produce downloads of the analysis, or integrate with external ERP or vendor-portal systems.

**Expected outcome:** A transparent quotation assessment linked to the selected RFQ, with structured vendor comparisons, clear coverage and exception reporting, traceable evidence, and a Purchase Proposal that the analyst builds from a plain-language request, with split purchases allowed where the buyer asks for them. The system must communicate when the available information is insufficient for a reliable comparison.

## 4. MVP Scope and Constraints

These are intentional product decisions for the MVP, not unfinished features.

**Session-only and low-cost**
- No database, user accounts, or login. RFQs, uploads, and analysis exist only for the current browser session; a refresh or session expiry clears them.
- Quotations are always evaluated against an RFQ saved in the same session.
- AI uses the Google Gemini API, with cost kept low by using code first and AI only where it adds value.

**Item catalogue**
- The product database is the United Nations Standard Products and Services Code (UNSPSC), published at [https://www.ungm.org/Public/UNSPSC](https://www.ungm.org/Public/UNSPSC). The product uses a trimmed copy limited to the segments relevant to refinery and process-plant MRO purchasing. The commodity title serves as the product name; the RFQ carries only an item, a quantity, and a unit.

**Units**
- The standard unit list is: Nos, Set, Pair, Kit, Kg, Tonne, Metre, Litre, Box, Pack, Roll, and Drum.
- Conversions are applied only between weight units (Kg, Tonne, grams), length units (Metre, centimetres, millimetres, kilometres), and volume units (Litre, millilitres, kilolitres). Count units are never converted into each other.

**Out of scope**
- Sending RFQs to vendors, vendor portals, approvals, purchase orders, ERP integration, persistent history, editing or deleting saved RFQs, image uploads, and email ingestion.

## 5. Agentic Workflows

The product uses AI where language understanding adds value, and ordinary software everywhere accuracy and repeatability matter. The buyer stays in control at every step.

### 5.1 What the AI does

| Action | What the AI does | What the software does | Buyer control |
|---|---|---|---|
| Understand the request | Splits a free-text request into items, quantities, and units, using the buyer's own words | Checks that every extracted value really appears in the request | Edits any row; unclear items are flagged, not guessed |
| Choose the catalogue item | Picks the best entry from a shortlist when the match is not obvious | Builds the shortlist, selects clear matches itself, and rejects any choice outside the shortlist | Changes the item through the picker; acknowledges unmatched items |
| Read vendor quotations | Transcribes vendor, lines, prices, units, and charges from messy files as written | Parses the values, checks them against the source document, and keeps the evidence | Corrects vendor names and flagged lines |
| Match quote lines to RFQ items | Judges unclear matches and explains differences (for example, a different size) | Matches clear lines itself and downgrades weak matches | Accepts, corrects, or excludes each flagged match |
| Answer questions (the analyst) | Decides which calculation answers the question and explains the result, including what-if questions | Runs every calculation and produces every figure, table, and chart | Sees the assumptions used and how each result was calculated; clears assumptions |

The AI never calculates totals, ranks vendors, converts currencies, or recommends an award. It cannot send anything outside the product or act on the buyer's behalf.

### 5.2 Key programmatic verifications

These checks run in software on every AI output. Anything doubtful appears in the Review summary instead of being silently accepted or silently discarded.

1. **No invented values:** every quantity, price, and unit the AI reports must be found in the buyer's request or the vendor's document.
2. **Real catalogue items only:** a selected item must come from the shortlist and its name is read from the catalogue, never from the AI.
3. **Evidence check:** each extracted line must point to a real row or page, and the quoted text must be there.
4. **Arithmetic check:** quantity times unit price must match the vendor's line total, and line totals must match the stated grand total.
5. **Completeness check:** the number of lines extracted is compared with the rows in the vendor's table, to catch silently missed lines.
6. **Unit and price-basis check:** units are mapped to the standard list; "per 100" style prices are normalized; units that cannot be compared are flagged, never guessed.
7. **Price outlier check:** a price far above or below other vendors' prices for the same item is flagged as a possible unit or decimal error.
8. **Zero and missing prices:** a zero price is flagged, and a missing price is never treated as zero.
9. **Match sanity check:** a match the AI calls "same item" is downgraded if the wording or sizes do not support it.
10. **Answer check:** every figure in an analyst answer must come from a calculation the software performed; award-style wording is blocked.

### 5.3 Why an AI judge is not used in the MVP

Some edge cases need semantic judgement that simple rules cannot settle, such as whether a vendor's substitute product is technically equivalent to the item requested, or whether a free-text deviation note matters commercially. A full product could add a second AI model as an independent judge to review such cases before they reach the buyer.

The MVP deliberately does not. A judge adds cost and delay on every call, its own opinions can be wrong and would need checking, and the free-tier limits are tight. Instead the MVP relies on the programmatic checks above, conservative flagging, and buyer review, which keeps the buyer as the judge of technical equivalence. An AI judge is a candidate for a later version if buyers find too many flagged items to review manually.

### 5.4 Workflow 1: Generate an RFQ (as built and tested live)

The first workflow turns a free-text purchasing request into a reviewed RFQ. It uses **two AI calls**, and most of the work is done by ordinary software around them.

```
Buyer's request
   │
   ├─ Software: check the input (empty, too long, not text)
   ├─ AI call G1, "parse":  split the request into items; extract quantity and unit as written;
   │                        suggest catalogue-style search terms
   ├─ Software: confirm each value really appears in the request; parse quantities and units
   ├─ Software: shortlist up to 8 catalogue candidates per item (fuzzy word match);
   │            pick clear winners itself; flag the rest
   ├─ AI call G2, "resolve": only for unclear items; choose one candidate from the shortlist, or none
   ├─ Software: accept the AI's choice only if it is in the shortlist and the word match supports it
   └─ Buyer: reviews the table and the Review summary, edits, accepts, saves
```

**Model and call set-up**

| Setting | Value | Why |
|---|---|---|
| Provider and SDK | Google Gemini API, `google-genai` Python SDK (the only AI library) | One provider, simplest integration, no agent framework needed for fixed two-step calls |
| Model | `gemini-3.5-flash-lite` for both calls (set in configuration, not in code) | The cheapest, fastest tier is enough: extraction over a short text and choosing from a list of 8. A larger `gemini-3.5-flash` is reserved for later document extraction |
| Call type | Single-turn, no tools, no conversation memory | Fixed inputs and outputs; the application controls the flow |
| Instructions | A versioned prompt file per call, sent as the system instruction | Prompts are reviewable and changeable without touching code |
| Output format | JSON enforced by a response schema, then validated again by the application | Downstream steps never read free text |
| Temperature | Provider default (Gemini 3 guidance); 0.1 is used only for the older 2.5 family | Newer models are tuned for their default; the schema keeps output stable |
| Reasoning effort | Minimal | Extraction and list selection need no deep reasoning; keeps latency and cost low |
| Output limit | 16,000 tokens | Large enough for about 100 items, and a response that hits the limit is treated as a failure, never as a partial result |
| Timeout and retries | 90 seconds; one retry only for server errors; a rate limit is never retried automatically | Avoids hammering a free-tier quota |
| Network | IPv4 forced | An unresponsive IPv6 route to Google made calls hang during testing |
| Guardrails on volume | At most 12,000 characters, 100 items, and 60 AI calls per session | Cost control and abuse protection on a public demo |

**Call G1: parse the request**
- **Input:** the buyer's text, wrapped in `<request>` tags and declared to be untrusted data.
- **Output:** an input classification (`procurement_request`, `unrelated` or `unintelligible`), and for each item: the exact wording from the request, the product name, up to three catalogue-style search terms, the quantity and unit **exactly as written** (or null), and an optional question.
- **Prompt design:** the rules say never infer a quantity or unit and never default to one; split compound lines; expand abbreviations such as "PT" into "pressure transmitter"; return nothing for requests that are not about goods. It includes two worked examples, one of them a negative case ("Hi, can you help me?"), and instructs the model to ignore any instructions inside the request.

**Call G2: choose the catalogue item**
- **Input:** for each unclear item, the buyer's wording and its shortlist of up to 8 catalogue candidates (code, title, class). Items are sent in batches of 30 per call.
- **Output:** for each item, one chosen code or none, a confidence (high, medium or low), a reason of up to 20 words, and up to three alternatives.
- **Prompt design:** the model may only choose from the supplied list and must answer "none" rather than pick the closest-sounding entry. It is told to match the kind of product, not a shared word ("hex bolts" are hexagonal bolts, not anchor bolts). It includes a worked example.
- **When it runs:** only when the software cannot decide, so many requests need one call, not two.

**Who decides what**

| Decision | Made by |
|---|---|
| Splitting the request into items, reading wording and abbreviations | AI (G1) |
| Whether each extracted value appears in the request | Software |
| Turning "ten", "1,000" or "a dozen" into numbers; mapping units to the standard list | Software |
| Shortlisting catalogue candidates; picking an obvious winner | Software |
| Choosing between similar candidates | AI (G2), then checked by software |
| Accepting, correcting or rejecting every uncertain line | The buyer |

**How the output is protected.** The AI's answer is validated against the schema; every extracted quantity and name is checked against the original text; a chosen code must be in the shortlist and its title is read from the catalogue, not from the AI; a confident AI choice is applied automatically only if its word-match score is within 3 points of the best candidate, otherwise it is shown first as a suggestion. A truncated, invalid or rate-limited response never produces a partial RFQ: the buyer's text is kept and a short message is shown.

**Observed behaviour in live testing**

| Test | Calls | Time | Result |
|---|---|---|---|
| Short request, 4 items | 2 | 4.1 s | All four lines correct; "instrument cable" matched "Instrumentation Cable", "safety gloves" matched "Protective gloves"; "gasket" left for the buyer |
| Messy list, 35 lines (abbreviations, ranges, missing units, vague items) | 2 | 12.2 s | Most lines correct; ranges left blank; shared quantities split and left blank; vague items sent to the picker |

Two wrong automatic matches were found ("hex bolts" matched "Anchor bolts", "PTFE tape" matched "Fluoropolymers PTFE"), although the right catalogue entries existed. Two fixes followed: the prompt rule about matching the kind of product, and the software guard that only applies an AI choice the word match supports.

### 5.5 AI product considerations

- **Right-sized model.** The work is language understanding over short text, not open-ended reasoning, so the cheapest tier with minimal reasoning is used. Quality is protected by software checks and buyer review instead of a larger model.
- **Cost and latency.** Typically one or two calls per RFQ, about 4 to 12 seconds for lists up to 35 lines, on a small model. Code resolves clear matches without a call. Batching limits calls for long lists.
- **Structured outputs over free text.** Every AI answer is a schema-checked record, so uncertainty is a field (confidence, nulls, questions), not a sentence the product has to interpret.
- **Uncertainty is surfaced, not smoothed over.** Missing quantities stay blank, ranges stay blank, unknown units stay unrecognised, and unmatched items stay in the buyer's own words, each shown in the Review summary until the buyer decides.
- **Privacy and safety.** Only the request text (and catalogue candidates for unclear items) is sent; no keys, session data or other users' data. The request is treated as data, never as instructions. The API key is held outside the code and the repository.
- **Resilience to change.** Model identifiers live in configuration. During the build, the originally chosen model family was no longer open to new users, which was found by querying the provider's model list; the product switched models with no code change.
- **How quality is judged.** There is no separate evaluation suite in the MVP; behaviour is checked by live use on realistic and messy requests, by the runtime verifiers, and by tests that run against a scripted stand-in and never reach the live service. Two real failures found this way were turned into permanent safeguards (above).
- **Metrics worth tracking when this moves beyond a prototype.** AI calls per RFQ; time to a reviewed RFQ; share of lines matched automatically versus sent to the buyer; share of automatic matches the buyer later changes (the key quality signal); lines needing a quantity or unit fix; rate-limit and failure rates.
- **Known limits.** Matching quality depends on the catalogue wording (it holds product names, not specifications); a request without clear product names yields guidance rather than an RFQ; free-tier rate limits cap how many requests can run per minute.

### 5.6 Workflow 2: Read and align vendor quotations (as built and tested live)

The second workflow reads vendor files in any supported format and shows how each lines up with the RFQ. It uses **at most two AI calls per file**, and many files need only one.

```
Vendor file (xlsx, csv, tsv, docx, pdf)
   ├─ Software: check the file (real type, size, empty, protected, duplicate); parse it into text rows,
   │            each with a reference (sheet and row, paragraph, table row, PDF block)
   ├─ AI call G3, "read":  transcribe vendor, terms, lines, charges exactly as written, with the row reference
   ├─ Software: parse prices, quantities, units, currency, tax wording, dates; check every value against the source row
   ├─ Software: match lines to RFQ items by word similarity; clear matches need no AI
   ├─ AI call G4, "match": only for lines software cannot place; says matched, possible, extra, or no match, and why
   ├─ Software: verifiers raise flags (about 25 checks); an AI "matched" the words do not support is downgraded
   └─ Buyer: sees the alignment matrix and each vendor's flags; can only Accept or Exclude (no number is ever edited)
```

| Setting | G3 (read) | G4 (match) |
|---|---|---|
| Model | `gemini-3.5-flash` | `gemini-3.5-flash-lite` |
| Input | The document as tagged text rows (`[Offer!R12] ...`); image-only PDFs are sent as the PDF itself | The RFQ items (id, title, wording, quantity, unit) and only the unplaced vendor lines |
| Output | Schema-enforced JSON: vendor, reference, date, validity, payment and delivery terms, stated total; per line the description, quantity, unit, price, price basis, line total, currency, tax wording, lead time, minimum order, option label and remarks, all as text exactly as written, plus the row reference and a verbatim source quote; charges listed separately | Per line: the RFQ item id or none, a status (matched, possible, no match, extra), visible differences, an alternate flag, a reason of up to 20 words |
| Reasoning, temperature, limits | Minimal reasoning; provider default temperature; 16,000-token output limit; large files read in row chunks | Same |
| Calls per file | 1 | 0 or 1 |

**Design choices.** G3 sees only the document, never the RFQ, so it cannot bend what it reads toward what the buyer expects. Numbers come back as written and software parses them (Indian digit grouping, "Rs", "per 100"), which makes grounding checkable. Every value is checked against the row it came from. A missing price stays missing and is never read as zero. Totals, tax rows and freight rows become charges, not lines. Lines a vendor marks as optional are never matched to an RFQ item. A separate tax row means prices exclude tax; prices stated as tax-inclusive are only backed out when the rate is stated.

**What the checks catch** (all found on the five test quotations without any file-specific code): partial coverage, several options for one item, a minimum order above the RFQ quantity, a possible (not certain) match with the difference named, an unreadable validity, price per 100 units, quote-level discounts, mixed currencies, a unit that cannot be compared (Pack against Set), prices with no value ("same as last supply"), and a price about ten times the other vendors' prices.

**Live results.** One full pass over the five test quotations took 8 AI calls (11 across all testing, including re-runs after fixes).

| Quote | Format | G3 time | G4 | Lines | Result |
|---|---|---|---|---|---|
| Quote1 | Excel | about 8 s | not needed, code matched all 17 | 17 | Clean; validated |
| Quote2 | Excel, cover and terms sheets | about 30 s | about 1 s | 14 | Options, minimum order, possible match, unreadable validity |
| Quote3 | Word letter | about 16 s | about 1 s | 18 | Per-100 pricing and discount read; the optional kit treated as an extra |
| Quote4 | PDF with two tables | about 10 s | not needed | 17 | Mixed currency and the unit mismatch flagged |
| Quote5 | Gmail-style email PDF | about 12 s | about 2 s | 17 | All 17 items read from one paragraph; two unpriced lines kept missing; outlier flagged |

**Fixes made during testing** (each a general rule, none tied to a file): a tax amount listed as its own row now means prices exclude tax; a line with no price no longer also gets unit flags; optional extras are never matched to an RFQ item; a group of options counts once in the review count.

**Speed.** Reading was first measured at 8 to 30 seconds per file, most of it waiting for the model's first word and for it to write a long record. Three general changes brought this to about 5 seconds per file with the same extracted values on the formats tested: the model's answer was slimmed (short field names, empty fields left out, the source row copied only when a row holds several lines), which cut the written output by about half; the reading step uses the lighter `gemini-3.5-flash-lite` model, which matched the larger model's values on the spreadsheet, Word, table-PDF and email-style files; and the answer is streamed so each line appears on the loading screen the moment it is found. Two files are read at the same time (no more, to respect rate limits); only the network call runs in a worker, and everything that changes the session happens in the main thread. A rate limit on one file fails only that file.

**Limits.** Very large files are read in chunks; scanned images are sent natively but were not part of the test set; currency conversion and the cheapest-combination calculation come in the next workflow.

### 5.7 Workflow 3: The analyst and the Purchase Proposal (as built and tested live)

One model call per request. The model receives the RFQ, every eligible offer (already converted to one currency, before tax), the two summaries, the previous rules and recent turns, and returns **rules** plus a short reply with no figures. Code validates the rules against real ids, solves for the cheapest purchase that keeps them (whole units, splits allowed only when asked, vendor capacity and minimum orders respected), computes every figure, and writes the rule report from the actual result. Impossible rules are dropped and reported, never faked.

Measured on the five sample quotations: about 1.5 seconds per request with the light model (about 13 seconds with the larger model, identical rules), 15 live calls in total for building and testing. "Every responder" gave a total only a few rupees above the cheapest possible, and exactly the sum of the smallest price differences needed to give each vendor an item; "split purchases, cheapest" gave the unconstrained cheapest; pinned items raised the total by exactly the price differences; an unsupported request was declined; an instruction placed inside a request changed nothing.

