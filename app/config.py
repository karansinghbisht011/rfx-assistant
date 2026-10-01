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
API_TIMEOUT_SECONDS = 60
MAX_RETRIES = 2

# Limits (resource controls)
MAX_INPUT_CHARS = 4000
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
MATCH_LOW = 60

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
