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

/* Keep Streamlit's icon font (the rule above would otherwise turn icons into words) */
[data-testid="stIconMaterial"], [class*="material-symbols"] {{ font-family: 'Material Symbols Rounded' !important; }}

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

/* Slim top bar */
.topbar {{
    position: fixed; top: 0; left: 0; right: 0; height: 52px; z-index: 1000;
    display: flex; align-items: center; padding: 0 28px;
    background: rgba(255,255,255,0.94); backdrop-filter: blur(8px);
    border-bottom: 1px solid {BORDER}; box-shadow: 0 2px 12px rgba(27,42,65,0.06);
}}
.topbar .logo {{
    width: 30px; height: 30px; border-radius: 9px; margin-right: 10px; color: #fff; font-weight: 700;
    font-size: 0.78rem; display: flex; align-items: center; justify-content: center; letter-spacing: -0.02em;
    background: linear-gradient(135deg, {TEAL}, {INK}); box-shadow: 0 3px 8px rgba(14,124,123,0.35);
}}
.topbar .name {{ font-weight: 700; font-size: 1.05rem; letter-spacing: -0.01em; color: {INK}; }}
.topbar .name span {{ color: {TEAL}; }}
[data-testid="stMainBlockContainer"] {{ padding: 4.1rem 2rem 2rem; max-width: 1400px; }}

/* Tabs as pills */
[role="tablist"] {{
    gap: 0.4rem; background: #fff; padding: 0.35rem; border-radius: 14px; border: 1px solid {BORDER};
    box-shadow: 0 2px 8px rgba(27,42,65,0.06); width: fit-content; margin-bottom: 0.4rem;
}}
[role="tablist"]::before, [role="tablist"]::after {{ display: none !important; }}
[role="tab"] {{
    height: 2.2rem; padding: 0 1.1rem; border-radius: 10px; background: transparent;
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

/* App-controlled navigation: a segmented control styled as pill tabs */
[data-testid="stButtonGroup"] {{
    background: #fff; padding: 0.35rem; border-radius: 14px; border: 1px solid {BORDER}; width: fit-content;
    box-shadow: 0 2px 8px rgba(27,42,65,0.06); margin-bottom: 0.4rem; gap: 0.4rem;
}}
button[data-variant="segmented_control"] {{
    height: 2.2rem; padding: 0 1.1rem; border-radius: 10px !important; background: transparent !important;
    border: none !important; color: {INK}; font-weight: 500; box-shadow: none !important; margin: 0 !important;
    transition: all .2s ease;
}}
button[data-variant="segmented_control"]:hover {{ background: rgba(14,124,123,0.09) !important; transform: translateY(-1px); }}
button[data-variant="segmented_control"][data-selected="true"] {{
    background: linear-gradient(135deg, {TEAL}, {TEAL_DEEP}) !important; color: #fff; font-weight: 600;
    box-shadow: 0 4px 12px rgba(14,124,123,0.35) !important;
}}
button[data-variant="segmented_control"][data-selected="true"] * {{ color: #fff !important; }}

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

/* Loader */
.loader-title {{ font-weight: 700; font-size: 1.05rem; margin-bottom: 0.9rem; }}
.loader-bar {{ height: 5px; border-radius: 5px; background: #EDE9E0; overflow: hidden; margin-bottom: 1rem; }}
.loader-bar::after {{
    content: ""; display: block; height: 100%; width: 38%; border-radius: 5px;
    background: linear-gradient(90deg, {TEAL}, {SAFFRON}); animation: slide 1.3s ease-in-out infinite;
}}
@keyframes slide {{ 0% {{ transform: translateX(-110%); }} 100% {{ transform: translateX(270%); }} }}
@keyframes pulse {{ 0%, 100% {{ box-shadow: 0 0 0 0 rgba(14,124,123,0.5); }} 50% {{ box-shadow: 0 0 0 7px rgba(14,124,123,0); }} }}
.loader-steps {{ list-style: none; padding: 0; margin: 0; }}
.loader-steps li {{ display: flex; align-items: center; gap: 0.7rem; padding: 0.3rem 0; color: #A39E94; font-size: 0.95rem; transition: color .3s; }}
.loader-steps .dot {{ width: 18px; height: 18px; border-radius: 50%; border: 2px solid #D9D3C7; flex: none; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #fff; }}
.loader-steps li.active {{ color: {INK}; font-weight: 600; }}
.loader-steps li.active .dot {{ border-color: {TEAL}; background: {TEAL}; animation: pulse 1.1s infinite; }}
.loader-steps li.done {{ color: {INK}; }}
.loader-steps li.done .dot {{ border-color: {TEAL}; background: {TEAL}; }}
.loader-steps li.done .dot::before {{ content: "\\2713"; }}

/* Manage RFQs */
.stats {{ display: flex; gap: 0.8rem; margin: 0.2rem 0 1rem; flex-wrap: wrap; }}
.stat {{ background: #fff; border: 1px solid {BORDER}; border-radius: 14px; padding: 0.6rem 1.1rem; min-width: 130px;
    box-shadow: 0 4px 14px rgba(27,42,65,0.06); }}
.stat-n {{ font-size: 1.35rem; font-weight: 700; color: {INK}; line-height: 1.2; }}
.stat-l {{ font-size: 0.78rem; color: #6B7385; text-transform: uppercase; letter-spacing: 0.05em; }}

/* Summary chips */
.chip {{ display: inline-block; padding: 0.05rem 0.5rem; border-radius: 6px; font-size: 0.82rem; font-weight: 600; margin-right: 0.35rem; }}
.chip-fix {{ background: #FDE8E7; color: #B42318; }}
.chip-review {{ background: #FFF0D6; color: #B25E09; }}
.chip-reviewed {{ background: #DDF4E4; color: #17803D; }}
.chip-fixed {{ background: #D5EFEA; color: #0B6B5C; }}

[class*="st-key-card-loading"] {{ border-left: 4px solid {TEAL}; min-height: 430px; }}
[class*="st-key-building-text"] textarea {{ font-size: 1rem; line-height: 1.5; cursor: not-allowed; color: #3B455A; -webkit-text-fill-color: #3B455A; }}
[class*="st-key-building-text"] [data-baseweb="textarea"], [class*="st-key-building-text"] [data-testid="stTextAreaRootElement"] {{
    background: #fff; box-shadow: 0 4px 14px rgba(27,42,65,0.08);
}}

/* Notices */
.notice {{ border-radius: 12px; padding: 0.8rem 1rem; border: 1px solid; margin: 0.7rem 0; }}
.notice b {{ display: block; margin-bottom: 0.15rem; }}
.notice-warn {{ background: #FFF8EA; border-color: #F2DDB5; color: #6B4A0B; }}
.notice-error {{ background: #FFF3F2; border-color: #F3C9C6; color: #7A1F1A; }}
.notice-info {{ background: #F2F8FF; border-color: #D5E3F5; color: #1D4577; }}
.notice-ok {{ background: #F0FAF7; border-color: #BFE3DA; color: #0B5A4B; }}

/* Table rows and states */
.th {{ font-size: 0.72rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: #8A8576; }}
.rfq-title {{ font-size: 1.35rem; font-weight: 700; letter-spacing: -0.01em; line-height: 1.2; }}
.rfq-sub {{ color: #6B7385; font-size: 0.88rem; }}
[class*="st-key-row-"] {{
    background: #fff; border: 1px solid {BORDER}; border-left: 4px solid #2F9E8F; border-radius: 12px;
    padding: 0.4rem 0.8rem; box-shadow: 0 2px 8px rgba(27,42,65,0.05);
}}
[class*="st-key-row-"] [data-testid="stVerticalBlock"] {{ gap: 0.25rem; }}
[class*="st-key-row-"] button {{ padding: 0.4rem 0.5rem; white-space: nowrap; }}
[class*="st-key-row-fix"] {{ background: #FFF6F5; border-color: #F3C9C6; border-left-color: #D64545; }}
[class*="st-key-row-review"] {{ background: #FFFAF0; border-color: #F2DDB5; border-left-color: {SAFFRON}; }}
[class*="st-key-row-hint"] {{ background: #F5F9FF; border-color: #D5E3F5; border-left-color: #4C8DD6; }}
[class*="st-key-qty-bad"] [data-testid="stNumberInputContainer"], [class*="st-key-qty-bad"] [data-baseweb="input"],
[class*="st-key-unit-bad"] [role="group"], [class*="st-key-unit-bad"] [data-baseweb="select"] > div {{
    border: 1.5px solid #D64545 !important; box-shadow: 0 0 0 3px rgba(214,69,69,0.14) !important; background: #fff;
}}
[class*="st-key-unit-sug"] [role="group"], [class*="st-key-unit-sug"] [data-baseweb="select"] > div {{
    border: 1.5px dashed {TEAL} !important; box-shadow: 0 0 0 3px rgba(14,124,123,0.10) !important;
}}
[class*="st-key-card-review-summary"] {{ border-left: 4px solid {SAFFRON}; }}
[class*="st-key-card-clear"] {{ border-left: 4px solid #2F9E8F; background: #F0FAF7; }}
[class*="st-key-card-request"] {{ padding: 0.8rem 1rem; }}

/* Catalogue picker */
[data-testid="stPopoverBody"] {{ min-width: 540px !important; max-width: 600px !important; padding: 1rem 1.1rem; }}
[class*="st-key-search-"] input {{ font-size: 1.02rem; padding: 0.7rem 0.8rem; }}
.pick-meta {{ color: #6B7385; font-size: 0.8rem; margin: -0.3rem 0 0.5rem 0.2rem; }}
[data-testid="stChatInput"] textarea {{ min-height: 118px; font-size: 1rem; }}
[data-testid="stChatInput"] {{ border-radius: 14px; box-shadow: 0 4px 14px rgba(27,42,65,0.08); border: 1px solid {BORDER}; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def topbar() -> None:
    st.markdown(
        '<div class="topbar"><div class="logo">Rx</div><div class="name">RFx <span>Assistant</span></div></div>',
        unsafe_allow_html=True,
    )
