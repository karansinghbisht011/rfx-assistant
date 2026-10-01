"""Tests must never reach the live Gemini API: blank the key and models before the app imports config."""

import os

for name in ("GEMINI_API_KEY", "GEMINI_MODEL_LITE", "GEMINI_MODEL_EXTRACT", "GEMINI_CALL_LIMIT"):
    os.environ[name] = ""
