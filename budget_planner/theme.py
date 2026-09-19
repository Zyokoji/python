"""theme.py — visual layer for Budget Planner.

Design tokens, one global CSS injection, and a few reusable render
helpers, so pages stay readable and every screen looks like it belongs
to the same product.

Direction: a ledger viewed at night. Near-black green ground, surfaces
that lift by one quiet step rather than by drop shadows, hairline rules
instead of boxes. Color is reserved for meaning — money in, money out,
over or under budget — never decoration. Figures are tabular so columns
of numbers align.
"""

from __future__ import annotations

import html

import streamlit as st

# --------------------------------------------------------------------------- #
# Tokens
# --------------------------------------------------------------------------- #

GROUND = "#0E1512"      # page background, near-black green
SURFACE = "#161F1B"     # cards, sidebar
SURFACE_2 = "#1C2723"   # inputs, forms, hover
RULE = "#26332D"        # hairlines
RULE_SOFT = "#1E2A25"   # quieter hairlines

TEXT = "#E9EFEB"        # primary text
TEXT_SOFT = "#93A69C"   # secondary text
TEXT_FAINT = "#6B7D74"  # tertiary / disabled

ACCENT = "#3FBF9C"      # brand, interactive
ACCENT_DIM = "#2E8F75"
POSITIVE = "#45D19A"    # money in / under budget
NEGATIVE = "#FF7F68"    # money out / over budget
WARNING = "#E5B25C"     # approaching a limit

FONT_URL = "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"

_GLOBAL_CSS = f"""
<style>
@import url('{FONT_URL}');

html, body, [class*="st-"], button, input, textarea, select {{
    font-family: 'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
}}

.stApp {{ background: {GROUND}; }}

/* Content sits directly on the ground — no floating white slab, which
   is what made the light version feel boxed-in. Breathing room instead. */
.block-container {{
    padding: 2.6rem 3rem 4rem 3rem;
    max-width: 1220px;
}}

/* ---- Type ---- */
h1 {{
    font-size: 1.75rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.025em;
    color: {TEXT};
    margin-bottom: 0.15rem !important;
}}
h2, h3 {{
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: {TEXT_SOFT} !important;
    margin-top: 2.4rem !important;
    margin-bottom: 0.9rem !important;
}}
p, label, .stMarkdown {{ color: {TEXT}; }}
small, .stCaption {{ color: {TEXT_SOFT}; }}

.stMetric, .stat-value, .row-figure, .stDataFrame, .stNumberInput input {{
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum";
}}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {{
    background: {SURFACE};
    border-right: 1px solid {RULE_SOFT};
}}
section[data-testid="stSidebar"] a {{
    border-radius: 7px;
    font-weight: 500;
    color: {TEXT_SOFT} !important;
}}
section[data-testid="stSidebar"] a:hover {{
    background: {SURFACE_2};
    color: {TEXT} !important;
}}

/* ---- Buttons ---- */
.stButton > button, .stDownloadButton > button {{
    border-radius: 8px;
    border: 1px solid {RULE};
    background: {SURFACE};
    color: {TEXT};
    font-weight: 500;
    transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
    background: {SURFACE_2};
    border-color: {ACCENT_DIM};
    color: {ACCENT};
}}
.stFormSubmitButton > button {{
    border-radius: 8px;
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: #06110D;
    font-weight: 600;
}}
.stFormSubmitButton > button:hover {{
    background: #54D3AF;
    border-color: #54D3AF;
    color: #06110D;
}}
.stButton > button:focus-visible,
.stFormSubmitButton > button:focus-visible,
.stDownloadButton > button:focus-visible {{
    outline: 2px solid {ACCENT};
    outline-offset: 2px;
}}

/* ---- Inputs ---- */
.stTextInput input, .stNumberInput input, .stDateInput input,
.stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {{
    background: {SURFACE_2} !important;
    border-radius: 8px !important;
    border: 1px solid {RULE} !important;
    color: {TEXT} !important;
}}
.stTextInput input:focus, .stNumberInput input:focus {{
    border-color: {ACCENT} !important;
}}

div[data-testid="stForm"] {{
    background: {SURFACE};
    border: 1px solid {RULE_SOFT};
    border-radius: 12px;
    padding: 1.3rem 1.4rem 0.6rem 1.4rem;
}}
div[data-testid="stExpander"] {{
    background: {SURFACE};
    border: 1px solid {RULE_SOFT} !important;
    border-radius: 12px !important;
}}

/* ---- Progress: thin rules, not chunky pills ---- */
.stProgress > div > div {{ background: {RULE}; border-radius: 99px; height: 6px; }}
.stProgress > div > div > div {{ border-radius: 99px; }}
.stProgress p {{ font-size: 0.85rem !important; color: {TEXT_SOFT} !important; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 1.6rem; border-bottom: 1px solid {RULE_SOFT}; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 500; color: {TEXT_SOFT}; }}
.stTabs [aria-selected="true"] {{ color: {TEXT} !important; }}

hr {{ border-color: {RULE_SOFT}; }}
#MainMenu, footer, [data-testid="stDecoration"] {{ visibility: hidden; }}

@media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; animation: none !important; }}
}}
@media (max-width: 640px) {{
    .block-container {{ padding: 1.5rem 1.1rem 2.5rem 1.1rem; }}
    h1 {{ font-size: 1.45rem !important; }}
    .stat {{ flex: 1 1 50% !important; }}
}}

/* ---- Components ---- */

.ledger-sub {{
    color: {TEXT_SOFT};
    font-size: 0.93rem;
    margin-top: 0.1rem;
    margin-bottom: 1.8rem;
}}

.stat-row {{
    display: flex;
    flex-wrap: wrap;
    border: 1px solid {RULE_SOFT};
    border-radius: 12px;
    overflow: hidden;
    background: {SURFACE};
    margin-bottom: 0.4rem;
}}
.stat {{
    flex: 1 1 170px;
    padding: 1.05rem 1.25rem 1.15rem 1.25rem;
    border-right: 1px solid {RULE_SOFT};
}}
.stat:last-child {{ border-right: none; }}
.stat-label {{
    font-size: 0.73rem;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: {TEXT_FAINT};
    font-weight: 600;
    margin-bottom: 0.45rem;
}}
.stat-value {{
    font-size: 1.6rem;
    font-weight: 600;
    letter-spacing: -0.03em;
    line-height: 1.1;
    color: {TEXT};
}}
.stat-note {{ font-size: 0.76rem; color: {TEXT_FAINT}; margin-top: 0.3rem; }}

.pos {{ color: {POSITIVE} !important; }}
.neg {{ color: {NEGATIVE} !important; }}
.warn {{ color: {WARNING} !important; }}
.dim {{ color: {TEXT_SOFT} !important; }}

.row-item {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.65rem 0;
    border-bottom: 1px solid {RULE_SOFT};
    gap: 1rem;
}}
.row-item:last-child {{ border-bottom: none; }}
.row-name {{ font-weight: 500; color: {TEXT}; font-size: 0.95rem; }}
.row-meta {{ font-size: 0.8rem; color: {TEXT_FAINT}; }}
.row-figure {{ font-weight: 600; white-space: nowrap; font-size: 0.95rem; }}

.empty-note {{
    border: 1px dashed {RULE};
    border-radius: 12px;
    padding: 1.15rem 1.3rem;
    color: {TEXT_SOFT};
    font-size: 0.9rem;
    background: {SURFACE};
    line-height: 1.5;
}}
</style>
"""


def apply(page_title: str, page_icon: str, subtitle: str | None = None) -> None:
    """Set page config, inject global CSS, render the page heading.

    Call once at the top of every page, before any other Streamlit call.
    """
    st.set_page_config(page_title=f"{page_title} · Budget Planner", page_icon=page_icon, layout="wide")
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
    st.title(f"{page_icon} {page_title}")
    if subtitle:
        st.markdown(f"<div class='ledger-sub'>{html.escape(subtitle)}</div>", unsafe_allow_html=True)


def stat_row(stats: list[dict]) -> None:
    """One joined strip of figures, so they read as a single statement
    line rather than as disconnected cards.

    Each stat: {"label", "value", "tone": "pos"|"neg"|""|None, "note"}.
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
    """A ruled ledger line: name (+ meta) left, figure right."""
    meta_html = f"<div class='row-meta'>{html.escape(meta)}</div>" if meta else ""
    st.markdown(
        f"<div class='row-item'><div><div class='row-name'>{html.escape(name)}</div>{meta_html}</div>"
        f"<div class='row-figure {tone}'>{html.escape(figure)}</div></div>",
        unsafe_allow_html=True,
    )


def empty_note(message: str) -> None:
    """An empty state that says what to do next."""
    st.markdown(f"<div class='empty-note'>{html.escape(message)}</div>", unsafe_allow_html=True)


def caption(text: str, tone: str = "dim") -> None:
    st.markdown(f"<div class='row-meta {tone}'>{html.escape(text)}</div>", unsafe_allow_html=True)
