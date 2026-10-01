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

/* Step bar */
.stepper {{ display: flex; align-items: center; gap: 0.35rem; margin: 0.2rem 0 1rem; flex-wrap: wrap; }}
.step {{ display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.9rem 0.4rem 0.45rem; border-radius: 999px; font-size: 0.9rem;
    font-weight: 500; background: #fff; border: 1px solid {BORDER}; color: #6B7385; }}
.step-n {{ width: 22px; height: 22px; border-radius: 50%; background: #ECE8E0; color: #6B7385; display: inline-flex; align-items: center;
    justify-content: center; font-size: 0.78rem; font-weight: 700; }}
.step-active {{ background: linear-gradient(135deg, {TEAL}, {TEAL_DEEP}); color: #fff; border-color: transparent; box-shadow: 0 4px 12px rgba(14,124,123,0.3); font-weight: 600; }}
.step-active .step-n {{ background: rgba(255,255,255,0.25); color: #fff; }}
.step-done {{ color: {INK}; }} .step-done .step-n {{ background: {TEAL}; color: #fff; }}
.step-open {{ color: {INK}; }}
.step-locked {{ opacity: 0.55; }}
.step-line {{ height: 2px; width: 22px; background: #E3DED3; border-radius: 2px; }}
.step-line-done {{ background: {TEAL}; }}

/* Analysing screen */
[class*="st-key-card-analysing"] {{ border-left: 4px solid {TEAL}; padding: 1.2rem 1.5rem; }}
.an-head {{ display: flex; justify-content: space-between; align-items: baseline; }}
.an-title {{ font-size: 1.2rem; font-weight: 700; }}
.an-sub {{ color: #6B7385; font-size: 0.9rem; }}
.an-bar {{ height: 6px; border-radius: 6px; background: #EDE9E0; overflow: hidden; margin: 0.8rem 0 1.1rem; }}
.an-bar-fill {{ height: 100%; border-radius: 6px; transition: width .6s ease;
    background: linear-gradient(90deg, {TEAL}, {SAFFRON}, {TEAL}); background-size: 200% 100%; animation: shimmer 1.6s linear infinite; }}
@keyframes shimmer {{ 0% {{ background-position: 200% 0; }} 100% {{ background-position: -200% 0; }} }}
.an-tiles {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.7rem; margin-bottom: 1.1rem; }}
.an-tile {{ background: #FAF7F2; border: 1px solid {BORDER}; border-radius: 12px; padding: 0.6rem 0.8rem; }}
.an-n {{ font-size: 1.5rem; font-weight: 700; line-height: 1.1; color: {INK}; animation: pop .35s ease; }}
.an-l {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #6B7385; }}
@keyframes pop {{ 0% {{ transform: scale(0.8); opacity: 0.4; }} 100% {{ transform: scale(1); opacity: 1; }} }}
.an-files {{ display: flex; flex-direction: column; gap: 0.5rem; }}
.an-file {{ display: flex; align-items: center; gap: 0.8rem; padding: 0.6rem 0.8rem; border-radius: 12px; border: 1px solid {BORDER}; background: #fff; transition: all .3s ease; }}
.an-ico {{ font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em; padding: 0.35rem 0.45rem; border-radius: 8px; background: #ECE8E0; color: #5B6577; min-width: 46px; text-align: center; }}
.an-name {{ flex: 1; display: flex; flex-direction: column; gap: 0.15rem; }}
.an-name small {{ color: #6B7385; font-size: 0.82rem; }}
.an-mark {{ font-size: 1rem; font-weight: 700; width: 1.4rem; text-align: center; }}
.an-queued {{ opacity: 0.6; }}
.an-active {{ border-color: {TEAL}; background: #F2FAF8; animation: glow 1.6s ease-in-out infinite; }}
@keyframes glow {{ 0%, 100% {{ box-shadow: 0 0 0 0 rgba(14,124,123,0.25); }} 50% {{ box-shadow: 0 0 0 6px rgba(14,124,123,0); }} }}
.an-done .an-mark {{ color: #17803D; animation: pop .4s ease; }} .an-done .an-ico {{ background: #DDF4E4; color: #17803D; }}
.an-rejected, .an-failed {{ background: #FFF6F5; border-color: #F3C9C6; }} .an-rejected .an-mark, .an-failed .an-mark {{ color: #B42318; }}
.an-feed {{ display: flex; flex-direction: column; gap: 0.15rem; margin-top: 0.2rem; }}
.an-line {{ font-size: 0.82rem; color: {INK}; padding: 0.1rem 0 0.1rem 0.6rem; border-left: 2px solid {TEAL};
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; animation: slidein .35s ease; }}
@keyframes slidein {{ from {{ opacity: 0; transform: translateX(-10px); }} to {{ opacity: 1; transform: none; }} }}
.an-stages {{ display: flex; gap: 0.35rem; flex-wrap: wrap; }}
.an-st {{ font-size: 0.78rem; padding: 0.12rem 0.55rem; border-radius: 999px; background: #ECE8E0; color: #8A8576; }}
.an-st.done {{ background: #D5EFEA; color: #0B6B5C; }}
.an-st.active {{ background: {TEAL}; color: #fff; animation: pulse 1.1s infinite; }}

/* Alignment matrix */
.matrix-wrap {{ overflow-x: auto; border-radius: 14px; border: 1px solid {BORDER}; background: #fff; box-shadow: 0 6px 18px rgba(27,42,65,0.07); }}
table.matrix {{ border-collapse: collapse; width: 100%; font-size: 0.88rem; }}
table.matrix th {{ background: #F6F3EC; text-align: left; padding: 0.55rem 0.7rem; font-weight: 600; vertical-align: bottom; border-bottom: 1px solid {BORDER}; }}
table.matrix th small {{ display: block; font-weight: 400; color: #6B7385; font-size: 0.75rem; }}
table.matrix td {{ padding: 0.45rem 0.7rem; border-bottom: 1px solid #F0ECE3; }}
table.matrix td.item {{ font-weight: 500; }} table.matrix td.item small {{ color: #6B7385; font-weight: 400; margin-left: 0.3rem; }}
.mx {{ display: inline-block; padding: 0.12rem 0.55rem; border-radius: 8px; font-size: 0.82rem; font-weight: 600; white-space: nowrap; }}
.mx-ok {{ background: #DDF4E4; color: #17803D; }} .mx-review {{ background: #FFF0D6; color: #B25E09; }}
.mx-possible {{ background: #E8F0FB; color: #1D4577; }} .mx-missing {{ background: #F1EEE8; color: #9A958B; font-weight: 500; }}
.mx-options {{ background: #EFE6FA; color: #5B2F91; }} .mx-excluded {{ background: #F1EEE8; color: #9A958B; text-decoration: line-through; }}
.cov {{ display: inline-block; margin-top: 0.2rem; padding: 0.05rem 0.45rem; border-radius: 6px; font-size: 0.72rem; font-weight: 700; background: #D5EFEA; color: #0B6B5C; }}
.tot {{ display: block; margin-top: 0.25rem; font-size: 0.95rem; font-weight: 700; color: {INK}; }}
.cov-part {{ background: #FFF0D6; color: #B25E09; }}
.terms {{ color: #6B7385; font-size: 0.85rem; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def topbar() -> None:
    st.markdown(
        '<div class="topbar"><div class="logo">Rx</div><div class="name">RFx <span>Assistant</span></div></div>',
        unsafe_allow_html=True,
    )
