"""Central settings. Model IDs, limits and thresholds live here, not in UI code."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

CATALOGUE_PATH = ROOT / "data" / "unspsc_catalogue.csv"

CANONICAL_UNITS = (
    "Nos", "Set", "Pair", "Kit", "Kg", "Tonne", "Metre", "Litre", "Box", "Pack", "Roll", "Drum",
)
# Count units are never converted into each other (a Box or Pack has no fixed size).
COUNT_UNITS = ("Nos", "Set", "Pair", "Kit", "Box", "Pack", "Roll", "Drum")

# Gemini. Model IDs are deliberately not hardcoded: set them in .env once the API key exists
# and current model availability, limits and pricing have been checked.
MODEL_LITE = os.getenv("GEMINI_MODEL_LITE", "")      # G1, G2, G4
MODEL_EXTRACT = os.getenv("GEMINI_MODEL_EXTRACT", "")  # G3, G5
GENERATION_TEMPERATURE = 0.1  # check the selected model's guidance before pinning
API_TIMEOUT_SECONDS = 90
MAX_RETRIES = 1  # one retry for transient server errors; rate limits are never retried blindly
FORCE_IPV4 = True  # some networks drop IPv6 to Google, which makes calls hang until the timeout
MAX_OUTPUT_TOKENS = 16000
RESOLVE_BATCH_SIZE = 30  # items per catalogue-resolve call

# Limits (resource controls)
MAX_INPUT_CHARS = 12000
MAX_ITEMS = 100
MAX_FILE_MB = 10
MAX_PDF_PAGES = 30
MAX_SHEET_ROWS = 2000
MAX_CALLS_PER_SESSION = 60
MAX_TOOL_ROUNDS = 4
MAX_CLARIFICATION_TURNS = 3
QUANTITY_CAP = 1_000_000

# Catalogue matching thresholds (0-100, tuned by hand while building)
SHORTLIST_SIZE = 8
MATCH_HIGH = 90
MATCH_MARGIN = 8
MATCH_PICK_TOLERANCE = 3  # an AI pick is applied automatically only if its score is this close to the best candidate
MATCH_LOW = 82  # below this, even a partial-word match is treated as noise

# Quotation matching and reading
MATCH_LINE_HIGH = 90          # a vendor line this similar to exactly one RFQ item is matched by code
MATCH_LINE_MARGIN = 15        # ...and must lead the next RFQ item by this much
MATCH_LINE_LOW = 55           # an AI "matched" below this word similarity is downgraded to "possible"
QUOTE_CALL_SPACING_SECONDS = 1.5  # pause between files when they are read one after another
QUOTE_CONCURRENCY = 2             # files read at the same time; kept low so a free-tier rate limit is not hit
PRICE_TOLERANCE = 0.01        # relative tolerance for quantity x price = total

# Price outlier check: flag prices beyond this multiple of the median of other vendors
PRICE_OUTLIER_FACTOR = 10


def get_api_key() -> str | None:
    """Gemini key from the environment locally, or Streamlit secrets when deployed. Never logged."""
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key
    try:
        import streamlit as st

        return st.secrets.get("GEMINI_API_KEY")
    except Exception:
        return None
