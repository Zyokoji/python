"""theme.py — visual layer for Budget Planner.

Design tokens, global CSS injection, a dark/light switch, and a few
reusable render helpers.

Two things worth knowing:

1. The theme is forced in CSS rather than left to .streamlit/config.toml.
   Streamlit only reads that file from the *current working directory*,
   so launching with `streamlit run budget_planner/app.py` from a parent
   folder silently drops it and you get the stock white theme. Injecting
   the palette means the app looks right no matter where it's launched
   from. config.toml is still shipped, as a belt-and-braces default.

2. The chosen mode is persisted in the app_settings table, so it
   survives restarts rather than resetting every session.

Direction: a ledger. Surfaces lift by one quiet step instead of using
drop shadows; hairlines instead of boxes. Color is reserved for meaning
— money in, money out, over or under budget — never decoration. Figures
are tabular so columns of numbers align.
"""

from __future__ import annotations

import html

import streamlit as st

DARK = {
    "ground": "#0E1512",
    "surface": "#161F1B",
    "surface2": "#1C2723",
    "rule": "#26332D",
    "rule_soft": "#1E2A25",
    "text": "#E9EFEB",
    "text_soft": "#93A69C",
    "text_faint": "#6B7D74",
    "accent": "#3FBF9C",
    "accent_hover": "#54D3AF",
    "on_accent": "#06110D",
    "positive": "#45D19A",
    "negative": "#FF7F68",
    "warning": "#E5B25C",
}

LIGHT = {
    "ground": "#F2F5F1",
    "surface": "#FFFFFF",
    "surface2": "#F7F9F6",
    "rule": "#D5DED8",
    "rule_soft": "#E2E9E4",
    "text": "#16211C",
    "text_soft": "#53635B",
    "text_faint": "#6E7E75",
    "accent": "#0F6B57",
    "accent_hover": "#0B5546",
    "on_accent": "#FFFFFF",
    "positive": "#15724A",
    "negative": "#B03F28",
    "warning": "#8A5710",
}

PALETTES = {"dark": DARK, "light": LIGHT}
DEFAULT_MODE = "dark"

FONT_URL = "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"


# --------------------------------------------------------------------------- #
# Mode handling
# --------------------------------------------------------------------------- #


def _read_mode_from_db() -> str:
    """Load the saved mode, tolerating any DB problem by falling back."""
    try:
        import database as db
        import db_session

        conn = db_session.get_shared_connection()
        mode = db.get_setting(conn, "ui_theme", DEFAULT_MODE)
        return mode if mode in PALETTES else DEFAULT_MODE
    except Exception:
        return DEFAULT_MODE


def get_mode() -> str:
    if "ui_theme" not in st.session_state:
        st.session_state["ui_theme"] = _read_mode_from_db()
    return st.session_state["ui_theme"]


def set_mode(mode: str) -> None:
    if mode not in PALETTES:
        mode = DEFAULT_MODE
    st.session_state["ui_theme"] = mode
    try:
        import database as db
        import db_session

        db.set_setting(db_session.get_shared_connection(), "ui_theme", mode)
    except Exception:
        pass  # a failed persist shouldn't stop the UI from switching


def colors() -> dict:
    return PALETTES[get_mode()]


def chart_colors() -> dict:
    c = colors()
    return {"accent": c["accent"], "positive": c["positive"], "negative": c["negative"]}


# --------------------------------------------------------------------------- #
# CSS
# --------------------------------------------------------------------------- #


def _css(c: dict) -> str:
    return f"""
<style>
@import url('{FONT_URL}');

html, body, [class*="st-"], button, input, textarea, select {{
    font-family: 'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
}}

/* Force the ground colour on every surface Streamlit paints, so the
   theme holds even when config.toml isn't picked up. */
.stApp, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
    background: {c['ground']} !important;
    color: {c['text']};
}}
[data-testid="stHeader"], [data-testid="stToolbar"] {{
    background: transparent !important;
}}

.block-container {{
    padding: 2.6rem 3rem 4rem 3rem;
    max-width: 1220px;
}}

h1 {{
    font-size: 1.75rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.025em;
    color: {c['text']} !important;
    margin-bottom: 0.15rem !important;
}}
h2, h3 {{
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: {c['text_soft']} !important;
    margin-top: 2.4rem !important;
    margin-bottom: 0.9rem !important;
}}
p, label, .stMarkdown, li {{ color: {c['text']}; }}

.stat-value, .row-figure, .stDataFrame, .stNumberInput input {{
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum";
}}

section[data-testid="stSidebar"] {{
    background: {c['surface']} !important;
    border-right: 1px solid {c['rule_soft']};
}}
section[data-testid="stSidebar"] a {{
    border-radius: 7px;
    font-weight: 500;
    color: {c['text_soft']} !important;
}}
section[data-testid="stSidebar"] a:hover {{
    background: {c['surface2']};
    color: {c['text']} !important;
}}

.stButton > button, .stDownloadButton > button {{
    border-radius: 8px;
    border: 1px solid {c['rule']};
    background: {c['surface']};
    color: {c['text']};
    font-weight: 500;
    transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
    background: {c['surface2']};
    border-color: {c['accent']};
    color: {c['accent']};
}}
.stFormSubmitButton > button {{
    border-radius: 8px;
    background: {c['accent']};
    border: 1px solid {c['accent']};
    color: {c['on_accent']};
    font-weight: 600;
}}
.stFormSubmitButton > button:hover {{
    background: {c['accent_hover']};
    border-color: {c['accent_hover']};
    color: {c['on_accent']};
}}
.stButton > button:focus-visible,
.stFormSubmitButton > button:focus-visible,
.stDownloadButton > button:focus-visible {{
    outline: 2px solid {c['accent']};
    outline-offset: 2px;
}}

.stTextInput input, .stNumberInput input, .stDateInput input,
.stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {{
    background: {c['surface2']} !important;
    border-radius: 8px !important;
    border: 1px solid {c['rule']} !important;
    color: {c['text']} !important;
}}
.stTextInput input:focus, .stNumberInput input:focus {{ border-color: {c['accent']} !important; }}

div[data-testid="stForm"] {{
    background: {c['surface']};
    border: 1px solid {c['rule_soft']};
    border-radius: 12px;
    padding: 1.3rem 1.4rem 0.6rem 1.4rem;
}}
div[data-testid="stExpander"] {{
    background: {c['surface']};
    border: 1px solid {c['rule_soft']} !important;
    border-radius: 12px !important;
}}

.stProgress > div > div {{ background: {c['rule']}; border-radius: 99px; height: 6px; }}
.stProgress > div > div > div {{ border-radius: 99px; }}
.stProgress p {{ font-size: 0.85rem !important; color: {c['text_soft']} !important; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 1.6rem; border-bottom: 1px solid {c['rule_soft']}; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 500; color: {c['text_soft']}; }}
.stTabs [aria-selected="true"] {{ color: {c['text']} !important; }}

hr {{ border-color: {c['rule_soft']}; }}
#MainMenu, footer, [data-testid="stDecoration"] {{ visibility: hidden; }}

@media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; animation: none !important; }}
}}
@media (max-width: 640px) {{
    .block-container {{ padding: 1.5rem 1.1rem 2.5rem 1.1rem; }}
    h1 {{ font-size: 1.45rem !important; }}
    .stat {{ flex: 1 1 50% !important; }}
}}

.ledger-sub {{
    color: {c['text_soft']};
    font-size: 0.93rem;
    margin-top: 0.1rem;
    margin-bottom: 1.8rem;
}}

.stat-row {{
    display: flex;
    flex-wrap: wrap;
    border: 1px solid {c['rule_soft']};
    border-radius: 12px;
    overflow: hidden;
    background: {c['surface']};
    margin-bottom: 0.4rem;
}}
.stat {{
    flex: 1 1 170px;
    padding: 1.05rem 1.25rem 1.15rem 1.25rem;
    border-right: 1px solid {c['rule_soft']};
}}
.stat:last-child {{ border-right: none; }}
.stat-label {{
    font-size: 0.73rem;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: {c['text_faint']};
    font-weight: 600;
    margin-bottom: 0.45rem;
}}
.stat-value {{
    font-size: 1.6rem;
    font-weight: 600;
    letter-spacing: -0.03em;
    line-height: 1.1;
    color: {c['text']};
}}
.stat-note {{ font-size: 0.76rem; color: {c['text_faint']}; margin-top: 0.3rem; }}

.pos {{ color: {c['positive']} !important; }}
.neg {{ color: {c['negative']} !important; }}
.warn {{ color: {c['warning']} !important; }}
.dim {{ color: {c['text_soft']} !important; }}

.row-item {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.65rem 0;
    border-bottom: 1px solid {c['rule_soft']};
    gap: 1rem;
}}
.row-item:last-child {{ border-bottom: none; }}
.row-name {{ font-weight: 500; color: {c['text']}; font-size: 0.95rem; }}
.row-meta {{ font-size: 0.8rem; color: {c['text_faint']}; }}
.row-figure {{ font-weight: 600; white-space: nowrap; font-size: 0.95rem; }}

.empty-note {{
    border: 1px dashed {c['rule']};
    border-radius: 12px;
    padding: 1.15rem 1.3rem;
    color: {c['text_soft']};
    font-size: 0.9rem;
    background: {c['surface']};
    line-height: 1.5;
}}
</style>
"""


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def apply(page_title: str, page_icon: str, subtitle: str | None = None) -> None:
    """Set page config, inject the palette, draw the mode switch and heading.

    Call once at the top of every page, before any other Streamlit call.
    """
    st.set_page_config(page_title=f"{page_title} · Budget Planner", page_icon=page_icon, layout="wide")
    mode = get_mode()
    st.markdown(_css(colors()), unsafe_allow_html=True)
    render_mode_toggle()
    st.title(f"{page_icon} {page_title}")
    if subtitle:
        st.markdown(f"<div class='ledger-sub'>{html.escape(subtitle)}</div>", unsafe_allow_html=True)


def render_mode_toggle() -> None:
    """Sidebar switch between dark and light. Keyed so it never collides
    with a page's own widgets."""
    mode = get_mode()
    label = "☀️  Switch to light" if mode == "dark" else "🌙  Switch to dark"
    if st.sidebar.button(label, key="_theme_toggle", width="stretch"):
        set_mode("light" if mode == "dark" else "dark")
        st.rerun()


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
