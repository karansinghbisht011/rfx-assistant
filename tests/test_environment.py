import sqlite3
import sys


def test_python_version():
    assert sys.version_info >= (3, 12)


def test_imports():
    import docx, dotenv, fitz, google.genai, httpx, openpyxl, pandas, pydantic, rapidfuzz, reportlab, streamlit  # noqa: F401


def test_sqlite():
    con = sqlite3.connect(":memory:")
    assert con.execute("select 1").fetchone() == (1,)
