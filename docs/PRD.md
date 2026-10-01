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

7. **View the indicative multi-vendor combination**
   - The system calculates an indicative hybrid deal by selecting the lowest-priced eligible, comparable offer for each RFQ item, subject to the defined coverage and technical-compliance checks.
   - It shows the selected vendor and offer for each item, the resulting vendor split, and the combined calculated total.
   - Offers with unresolved technical equivalence, missing critical prices, or material commercial uncertainty are not silently treated as eligible. They are flagged and their effect on the hybrid calculation is explained.
   - The hybrid result is presented as an analytical recommendation for buyer review, not as an automatic award or purchase decision.

8. **Ask the analyst**
   - The user can ask questions about the comparison in plain language and receive answers as text, tables, and charts, with results downloadable as CSV or Excel.
   - The analyst handles what-if questions: which vendor is cheapest overall or per item, what happens if a vendor is excluded, what a split among at most N vendors would cost, which vendors cover every item, savings against a chosen vendor, what a vendor's stated freight, taxes, and discounts are, why a line was excluded or flagged, and what evidence supports a price.
   - Every figure shown is calculated by the application, not by the AI. The analyst states the assumptions it used (for example, "excluding Vendor B") and any exclusions, flags, or coverage gaps that affect the answer, and the user can see how each result was calculated.
   - When a question is ambiguous it asks one short clarifying question; when the quotations do not contain the information (for example, vendor reputation or delivery track record), it says so.
   - The analyst presents analysis for the buyer's consideration and never issues an award or purchase decision.
   - The user can download the analysis as a PDF including the comparison, both scenarios, currency details, the Review summary, and assumptions.

9. **Make the procurement decision**
   - The procurement manager reviews the item matches, quotation coverage, price comparisons, exceptions, and hybrid calculation.
   - The user retains responsibility for validating technical suitability, resolving commercial ambiguities, and making the final sourcing or award decision.
   - The MVP ends with the comparison and recommendation available for review. It does not send RFQs to vendors, negotiate, create purchase orders, execute awards, or integrate with external ERP or vendor-portal systems.

**Expected outcome:** A transparent quotation assessment linked to the selected RFQ, with structured vendor comparisons, clear coverage and exception reporting, traceable evidence, an indicative lowest-cost hybrid combination where comparable data supports one, and an analyst that answers follow-up and what-if questions from the same data. The system must communicate when the available information is insufficient for a reliable comparison.

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

## 5. AI Actions and Safeguards

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
