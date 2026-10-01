from pathlib import Path

from streamlit.testing.v1 import AppTest

MAIN = Path(__file__).resolve().parent.parent / "app" / "main.py"


def test_app_renders_three_tabs_without_errors():
    at = AppTest.from_file(str(MAIN), default_timeout=30).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Generate an RFQ", "Manage My RFQs", "Evaluate Quotations"]


def test_no_internal_status_text_in_ui():
    at = AppTest.from_file(str(MAIN), default_timeout=30).run()
    shown = [e.value for e in at.caption] + [e.value for e in at.info] + [e.value for e in at.markdown]
    assert not any("not enabled" in v.lower() or "session only" in v.lower() for v in shown)
