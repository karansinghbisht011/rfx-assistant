import sys
from pathlib import Path

# `streamlit run app/main.py` puts app/ on the path, not the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from app import state  # noqa: E402
from app.ui import evaluate_quotes_tab, manage_rfqs_tab, rfq_tab, theme  # noqa: E402

st.set_page_config(page_title="RFx Assistant", page_icon="📄", layout="wide")
state.init_state(st.session_state)
theme.inject_css()

theme.hero("RFx Assistant", "Turn procurement requests into RFQs and compare vendor quotations.")

generate_tab, manage_tab, evaluate_tab = st.tabs(["Generate an RFQ", "Manage My RFQs", "Evaluate Quotations"])
with generate_tab:
    rfq_tab.render(st.session_state)
with manage_tab:
    manage_rfqs_tab.render(st.session_state)
with evaluate_tab:
    evaluate_quotes_tab.render(st.session_state)
