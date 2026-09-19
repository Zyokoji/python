"""theme.py — visual layer for Budget Planner.

Holds the design tokens, one global CSS injection, and a small set of
reusable render helpers so the pages stay readable and every screen
looks like it belongs to the same product.

Design direction: a ledger, not a dashboard. Pale ledger-paper ground,
white "sheets" floating on it, deep ink-green text. Color is reserved
for meaning — money in, money out, over or under budget — never for
decoration. Figures are tabular so columns of numbers line up.
"""

from __future__ import annotations

import html

import streamlit as st

# --------------------------------------------------------------------------- #
# Tokens
# --------------------------------------------------------------------------- #

INK = "#16211C"        # primary text, deep green-black
INK_SOFT = "#5A6B62"   # secondary text
RULE = "#D8DFD7"       # hairlines and borders
PAPER = "#EFF2ED"      # page ground
SHEET = "#FFFFFF"      # card surface
ACCENT = "#0F6B57"     # primary brand green
POSITIVE = "#1B7A4B"   # money in / under budget
NEGATIVE = "#B03F28"   # money out / over budget
WARNING = "#9A6212"    # approaching a limit

FONT_URL = "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"

_GLOBAL_CSS = f"""
<style>
@import url('{FONT_URL}');

html, body, [class*="st-"], button, input, textarea, select {{
    font-family: 'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
}}

/* Ledger ground, with the main column as a floating sheet of paper. */
.stApp {{ background: {PAPER}; }}

.block-container {{
    background: {SHEET};
    border: 1px solid {RULE};
    border-radius: 10px;
    padding: 2.4rem 2.6rem 3rem 2.6rem;
    margin-top: 2.2rem;
    margin-bottom: 2.5rem;
    max-width: 1180px;
}}

/* Type scale. Headings are tight and confident; no all-caps eyebrows. */
h1 {{
    font-size: 1.9rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    color: {INK};
    margin-bottom: 0.2rem !important;
}}
h2 {{
    font-size: 1.18rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em;
    color: {INK};
    margin-top: 2rem !important;
    padding-bottom: 0.45rem;
    border-bottom: 1px solid {RULE};
}}
h3 {{
    font-size: 1.02rem !important;
    font-weight: 600 !important;
    color: {INK};
}}
p, label, .stMarkdown {{ color: {INK}; }}

/* Every figure in the app is tabular, so digits align in columns. */
.stMetric, .ledger-figure, .stDataFrame, .stNumberInput input {{
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum";
}}

/* Sidebar reads as the ledger's index tab. */
section[data-testid="stSidebar"] {{
    background: {SHEET};
    border-right: 1px solid {RULE};
}}
section[data-testid="stSidebar"] a {{
    border-radius: 6px;
    font-weight: 500;
}}

/* Buttons: solid for the primary action, quiet outline for everything else. */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
    border-radius: 7px;
    border: 1px solid {RULE};
    background: {SHEET};
    color: {INK};
    font-weight: 500;
    transition: background 120ms ease, border-color 120ms ease;
}}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
}}
.stFormSubmitButton > button {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #FFFFFF;
}}
.stFormSubmitButton > button:hover {{
    background: #0B5546;
    border-color: #0B5546;
    color: #FFFFFF;
}}
.stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible {{
    outline: 2px solid {ACCENT};
    outline-offset: 2px;
}}

/* Inputs */
.stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"] > div {{
    border-radius: 7px !important;
    border-color: {RULE} !important;
}}

/* Forms and expanders sit on a faintly tinted panel, not another white box. */
div[data-testid="stForm"] {{
    background: {PAPER};
    border: 1px solid {RULE};
    border-radius: 9px;
    padding: 1.15rem 1.25rem 0.5rem 1.25rem;
}}
details, div[data-testid="stExpander"] {{
    border-radius: 9px !important;
    border-color: {RULE} !important;
}}

/* Progress bars: thin ledger rules rather than chunky pills. */
.stProgress > div > div {{ background: {RULE}; border-radius: 3px; height: 7px; }}
.stProgress > div > div > div {{ border-radius: 3px; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 1.5rem; border-bottom: 1px solid {RULE}; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 500; }}

hr {{ border-color: {RULE}; }}
#MainMenu, footer {{ visibility: hidden; }}

@media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; animation: none !important; }}
}}

@media (max-width: 640px) {{
    .block-container {{ padding: 1.4rem 1.1rem 2rem 1.1rem; margin-top: 1rem; }}
    h1 {{ font-size: 1.55rem !important; }}
}}

/* ---- Custom components ---- */

.ledger-sub {{
    color: {INK_SOFT};
    font-size: 0.92rem;
    margin-top: 0.1rem;
    margin-bottom: 1.4rem;
}}

.stat-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    border: 1px solid {RULE};
    border-radius: 9px;
    overflow: hidden;
    margin-bottom: 0.5rem;
}}
.stat {{
    flex: 1 1 160px;
    padding: 0.95rem 1.15rem 1.05rem 1.15rem;
    border-right: 1px solid {RULE};
    background: {SHEET};
}}
.stat:last-child {{ border-right: none; }}
.stat-label {{
    font-size: 0.8rem;
    color: {INK_SOFT};
    font-weight: 500;
    margin-bottom: 0.3rem;
}}
.stat-value {{
    font-size: 1.5rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
    line-height: 1.15;
}}
.stat-note {{ font-size: 0.78rem; color: {INK_SOFT}; margin-top: 0.2rem; }}

.pos {{ color: {POSITIVE}; }}
.neg {{ color: {NEGATIVE}; }}
.warn {{ color: {WARNING}; }}
.dim {{ color: {INK_SOFT}; }}

.row-item {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.55rem 0;
    border-bottom: 1px solid {RULE};
    gap: 1rem;
}}
.row-item:last-child {{ border-bottom: none; }}
.row-name {{ font-weight: 500; }}
.row-meta {{ font-size: 0.82rem; color: {INK_SOFT}; }}
.row-figure {{ font-variant-numeric: tabular-nums; font-weight: 600; white-space: nowrap; }}

.empty-note {{
    border: 1px dashed {RULE};
    border-radius: 9px;
    padding: 1.1rem 1.2rem;
    color: {INK_SOFT};
    font-size: 0.9rem;
    background: {PAPER};
}}
</style>
"""


def apply(page_title: str, page_icon: str, subtitle: str | None = None) -> None:
    """Set page config, inject global CSS, and render the page heading.

    Call this once at the top of every page, immediately after the
    imports, before any other Streamlit call.
    """
    st.set_page_config(page_title=f"{page_title} · Budget Planner", page_icon=page_icon, layout="wide")
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
    st.title(f"{page_icon} {page_title}")
    if subtitle:
        st.markdown(f"<div class='ledger-sub'>{html.escape(subtitle)}</div>", unsafe_allow_html=True)


def stat_row(stats: list[dict]) -> None:
    """Render a joined row of figures.

    Each stat is {"label": str, "value": str, "tone": "pos"|"neg"|""|None,
    "note": str|None}. Rendered as one bordered strip so the numbers read
    as a single statement line rather than four disconnected cards.
    """
    cells = []
    for s in stats:
        tone = s.get("tone") or ""
        note = s.get("note")
        note_html = f"<div class='stat-note'>{html.escape(note)}</div>" if note else ""
        cells.append(
            f"<div class='stat'>"
            f"<div class='stat-label'>{html.escape(s['label'])}</div>"
            f"<div class='stat-value {tone}'>{html.escape(str(s['value']))}</div>"
            f"{note_html}</div>"
        )
    st.markdown(f"<div class='stat-row'>{''.join(cells)}</div>", unsafe_allow_html=True)


def line_item(name: str, figure: str, meta: str = "", tone: str = "") -> None:
    """A single ruled ledger line: name (+ meta) on the left, figure right."""
    meta_html = f"<div class='row-meta'>{html.escape(meta)}</div>" if meta else ""
    st.markdown(
        f"<div class='row-item'><div><div class='row-name'>{html.escape(name)}</div>{meta_html}</div>"
        f"<div class='row-figure {tone}'>{html.escape(figure)}</div></div>",
        unsafe_allow_html=True,
    )


def empty_note(message: str) -> None:
    """An empty state that tells the person what to do next."""
    st.markdown(f"<div class='empty-note'>{html.escape(message)}</div>", unsafe_allow_html=True)


def caption(text: str, tone: str = "dim") -> None:
    st.markdown(f"<div class='row-meta {tone}'>{html.escape(text)}</div>", unsafe_allow_html=True)
