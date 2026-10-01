"""Visual theme: injected once per run. Colors mirror .streamlit/config.toml."""

import streamlit as st

INK = "#1B2A41"
TEAL = "#0E7C7B"
TEAL_DEEP = "#0A5C5C"
SAFFRON = "#E9A23B"
CANVAS = "#FAF7F2"
BORDER = "#E7E2D9"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="st-"], button, input, textarea {{
    font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
}}

/* Hide Streamlit chrome: deploy button, menu, footer */
[data-testid="stToolbar"], [data-testid="stDeployButton"], #MainMenu, footer,
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent; height: 0; }}

.stApp {{
    background:
        radial-gradient(1200px 400px at 90% -10%, rgba(233,162,59,0.10), transparent 60%),
        radial-gradient(900px 400px at -10% 0%, rgba(14,124,123,0.08), transparent 55%),
        {CANVAS};
    color: {INK};
}}
.block-container {{ padding-top: 1.6rem; max-width: 1180px; }}

/* Hero */
.hero {{
    background: linear-gradient(120deg, {INK} 0%, #14506a 55%, {TEAL} 100%);
    border-radius: 18px;
    padding: 1.7rem 2rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 10px 30px rgba(27,42,65,0.18), 0 2px 6px rgba(27,42,65,0.10);
    position: relative;
    overflow: hidden;
}}
.hero::after {{
    content: ""; position: absolute; right: -40px; top: -40px; width: 180px; height: 180px;
    border-radius: 50%; background: radial-gradient(circle, rgba(233,162,59,0.45), transparent 70%);
}}
.hero h1 {{ color: #fff; font-size: 1.9rem; font-weight: 700; margin: 0; letter-spacing: -0.02em; padding: 0; }}
.hero p {{ color: rgba(255,255,255,0.82); margin: 0.35rem 0 0; font-size: 1rem; }}
.hero .accent {{ width: 44px; height: 4px; border-radius: 4px; background: {SAFFRON}; margin-bottom: 0.8rem; }}

/* Tabs as pills */
[role="tablist"] {{
    gap: 0.4rem; background: #fff; padding: 0.35rem; border-radius: 14px; border: 1px solid {BORDER};
    box-shadow: 0 2px 8px rgba(27,42,65,0.06); width: fit-content; margin-bottom: 0.6rem;
}}
[role="tablist"]::before, [role="tablist"]::after {{ display: none !important; }}
[role="tab"] {{
    height: 2.5rem; padding: 0 1.25rem; border-radius: 10px; background: transparent;
    color: {INK}; font-weight: 500; transition: all .2s ease; cursor: pointer;
}}
[role="tab"]:hover {{ background: rgba(14,124,123,0.09); transform: translateY(-1px); }}
[role="tab"][aria-selected="true"] {{
    background: linear-gradient(135deg, {TEAL}, {TEAL_DEEP}); color: #fff; font-weight: 600;
    box-shadow: 0 4px 12px rgba(14,124,123,0.35);
}}
[role="tab"][aria-selected="true"] p {{ color: #fff; }}
[role="tab"] .react-aria-SelectionIndicator {{ display: none !important; }}
[data-testid="stTabs"] {{ border-bottom: none; }}

h2, h3 {{ color: {INK}; letter-spacing: -0.01em; }}

/* Buttons */
.stButton > button, [data-testid^="stBaseButton"] {{
    border-radius: 10px; font-weight: 600; padding: 0.55rem 1.2rem;
    transition: transform .15s ease, box-shadow .15s ease;
}}
[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, {TEAL}, {TEAL_DEEP}); border: none; color: #fff;
    box-shadow: 0 4px 12px rgba(14,124,123,0.30), 0 1px 2px rgba(27,42,65,0.12);
}}
[data-testid="stBaseButton-primary"]:hover:not(:disabled) {{
    transform: translateY(-2px); box-shadow: 0 8px 20px rgba(14,124,123,0.38), 0 2px 4px rgba(27,42,65,0.14);
}}
[data-testid="stBaseButton-primary"]:active:not(:disabled) {{ transform: translateY(0); box-shadow: 0 2px 6px rgba(14,124,123,0.3); }}
[data-testid="stBaseButton-secondary"] {{
    background: #fff; border: 1px solid {BORDER}; color: {INK}; box-shadow: 0 2px 6px rgba(27,42,65,0.08);
}}
[data-testid="stBaseButton-secondary"]:hover:not(:disabled) {{
    border-color: {TEAL}; color: {TEAL_DEEP}; transform: translateY(-2px); box-shadow: 0 6px 14px rgba(27,42,65,0.12);
}}
.stButton > button:disabled {{
    background: #ECE8E0; color: #9A958B; border: 1px solid {BORDER}; box-shadow: none; cursor: not-allowed;
}}

/* Cards: st.container(border=True, key="card-...") */
[class*="st-key-card"] {{
    background: #fff; border: 1px solid {BORDER}; border-radius: 14px; padding: 1rem 1.2rem;
    box-shadow: 0 6px 18px rgba(27,42,65,0.07), 0 1px 3px rgba(27,42,65,0.06);
}}

/* Inputs */
[data-testid="stTextAreaRootElement"], [data-baseweb="textarea"], [data-baseweb="input"], [data-baseweb="select"] > div {{
    border-radius: 12px; background: #fff; border: 1px solid {BORDER};
    box-shadow: 0 1px 3px rgba(27,42,65,0.05); transition: all .2s ease;
}}
[data-baseweb="textarea"]:focus-within, [data-baseweb="input"]:focus-within {{
    border-color: {TEAL}; box-shadow: 0 0 0 3px rgba(14,124,123,0.18);
}}
[data-testid="stFileUploaderDropzone"] {{
    background: #fff; border: 1.5px dashed {SAFFRON}; border-radius: 14px;
}}
[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; box-shadow: 0 4px 14px rgba(27,42,65,0.07); }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, tagline: str) -> None:
    st.markdown(
        f'<div class="hero"><div class="accent"></div><h1>{title}</h1><p>{tagline}</p></div>',
        unsafe_allow_html=True,
    )
