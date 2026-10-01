import sys
from pathlib import Path

# `streamlit run app/main.py` puts app/ on the path, not the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from app import state  # noqa: E402
from app.ui import evaluate_quotes_tab, manage_rfqs_tab, nav, rfq_tab, theme  # noqa: E402

st.set_page_config(page_title="RFx Assistant", page_icon="📄", layout="wide")
state.init_state(st.session_state)
theme.inject_css()

theme.topbar()

page = nav.render()
if page == nav.PAGES[0]:
    rfq_tab.render(st.session_state)
elif page == nav.PAGES[1]:
    manage_rfqs_tab.render(st.session_state)
else:
    evaluate_quotes_tab.render(st.session_state)
