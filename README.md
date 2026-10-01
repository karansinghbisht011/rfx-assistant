# RFx Assistant

A lightweight procurement assistant for MRO (maintenance, repair and operations) purchasing in refinery and process-plant settings. It helps a buyer go from a plain-language request to a structured RFQ, and from a stack of vendor quotations to a clear, checked comparison and a proposed purchase.

**Live demo:** https://rfx-assistant1.streamlit.app/ (use the sample data below; a free app may take a few seconds to wake up).

Built with Python, Streamlit and the Google Gemini API. It is **session-only by design**: there is no database and no login, and refreshing the browser clears everything.

## What it does

The app has three screens.

**1. Generate an RFQ.** Describe what you need in natural language ("2 centrifugal pumps, 150 m of power cable, a dozen hex bolts..."). The app splits the request into items, matches each to a catalogue of standard commodity names, and flags anything unclear (missing quantities, ambiguous items, unusual units) for you to resolve. You review an editable table of item, quantity and unit, name the RFQ, and download it as a PDF.

**2. Manage My RFQs.** The RFQs saved in the current session are listed with their items. View them, download the PDF, or select one to evaluate quotations against.

**3. Evaluate Quotations.** A guided flow:
- **Upload** vendor quotations in PDF, Word, Excel or CSV. Several files are read at once, and each file is handled on its own, so one bad file never blocks the rest.
- **Review** how each quotation lines up with the RFQ. Every issue found (missing prices, unit differences, mixed currencies, unusually high prices, weak matches and so on) is listed per vendor. Nothing is silently dropped: you can accept an issue or exclude the line or vendor.
- **Compare** the quotations. The app shows the lowest offer for each item and each vendor's total, all on the same basis (unit price × RFQ quantity, before tax, in one currency, with exchange rates shown). An analyst chat lets you describe the purchase you want in plain language, for example "allow split purchases so the total is cheapest" or "include every vendor that responded", and returns a **Purchase Proposal** with the item, vendor, quantity, unit price and total for each line.

## How it works

- **Code first, AI for the rest.** File parsing, unit conversion, price and currency calculations, matching of clear cases, the review checks and the purchase optimisation are all deterministic code. Gemini reads the language: it extracts lines from the documents, matches the lines that are not clear, and turns a request into rules.
- **Figures always come from code.** The AI never calculates a price, a total or a ranking. For the analyst, it only sets rules (split allowed, vendors required or left out, and so on); the application finds the cheapest purchase that keeps them and shows the rules it understood.
- **Everything is checked.** Extracted values are kept as written and parsed by code, each line points back to its source row, and a set of verifiers raises flags instead of guessing.
- **Uploaded content is treated as data**, never as instructions.

## Documentation

The detailed specifications are in this repository:

- [`docs/PRD.md`](docs/PRD.md): the product requirements, user journeys and the agentic workflows.
- [`docs/implementation.md`](docs/implementation.md): the architecture, data contracts, Gemini call specifications, verifiers, UI design, testing and deployment notes.

## Quick start

Requires Python 3.12 or newer and a Google Gemini API key.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env
streamlit run app/main.py
```

Open http://localhost:8501.

### Configuration

Set these in `.env` (which is git-ignored; never commit it):

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key. Without it the app starts, but reading, matching and the analyst are unavailable. |
| `GEMINI_MODEL_LITE` | Model for RFQ parsing, catalogue resolution and quotation matching. |
| `GEMINI_MODEL_EXTRACT` | Model for reading quotation documents. |
| `GEMINI_MODEL_ANALYST` | Model for the analyst. |
| `MAX_CALLS_PER_SESSION` | Optional. Limit on AI calls per browser session (default 60). Lower it for a public demo. |

When deployed, put the same values in Streamlit secrets instead of a file. Limits (file size, rows, pages, calls per session) live in `app/config.py`.

### Tests

```bash
pytest
```

The tests never call the live Gemini API: a scripted stand-in is used.

## Deploying

The app runs on Streamlit Community Cloud. Connect the repository, set the main file to `app/main.py` and Python to 3.12, and put the configuration in the app's secrets:

```
GEMINI_API_KEY = "your key"
GEMINI_MODEL_LITE = "gemini-3.5-flash-lite"
GEMINI_MODEL_EXTRACT = "gemini-3.5-flash-lite"
GEMINI_MODEL_ANALYST = "gemini-3.5-flash-lite"
MAX_CALLS_PER_SESSION = "25"
```

A public app lets anyone use the key's quota, so keep `MAX_CALLS_PER_SESSION` low. Use sample or synthetic documents for public demos. Never commit the key.

## Try it with the sample data

`data/test_data/` holds five sample vendor quotations (Excel, Word, PDF tables and an email-style PDF), a reference RFQ, and `RFQ-prompt.md` with a request that produces a matching RFQ. Paste that prompt into **Generate an RFQ**, save the RFQ, then upload the five quotations in **Evaluate Quotations**. `data/test_data/EXPECTED.md` lists what each quotation contains, for checking the results by eye.

## Project layout

```
app/
  main.py            Streamlit entry point
  config.py          settings, limits, thresholds
  schemas/           Pydantic data contracts (RFQ, quotation, analyst, model outputs)
  services/          parsing, matching, verifiers, comparison, solver, Gemini client
  prompts/           the prompts for each Gemini call
  ui/                screens and components
data/                trimmed commodity catalogue and sample quotations
docs/                PRD and implementation specification
tests/               unit and integration tests
```

## Limitations

- Session-only: nothing is stored, and a refresh clears the session.
- Supported quotation formats are PDF, `.docx`, `.xlsx`, CSV and TSV. Legacy `.doc` and `.xls` files and standalone images are not accepted.
- Unit prices are taken as flat; volume discounts and quote-level discounts are shown but not applied.
- The output is decision support. The buyer remains responsible for technical suitability and the final award.
