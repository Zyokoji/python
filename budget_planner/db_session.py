"""Shared Streamlit resources: a single cached DB connection, reused
across every page and rerun instead of reopening the file each time,
plus a once-per-browser-session recurring-transaction sync.

Kept separate from database.py so that module stays Streamlit-free and
independently testable.
"""

from __future__ import annotations

import sqlite3

import streamlit as st

import config
import database as db


@st.cache_resource
def get_shared_connection() -> sqlite3.Connection:
    return db.get_connection()


def get_conn_and_sync() -> tuple[sqlite3.Connection, str]:
    """Return (connection, currency_symbol).

    Also runs process_recurring() exactly once per browser session, so
    navigating between pages doesn't repeatedly re-check every recurring
    item on every single rerun.
    """
    conn = get_shared_connection()
    if not st.session_state.get("_recurring_synced"):
        generated = db.process_recurring(conn)
        st.session_state["_recurring_synced"] = True
        if generated:
            st.toast(
                f"Generated {generated} recurring transaction{'s' if generated != 1 else ''}.",
                icon="🔁",
            )
    symbol = db.get_setting(conn, "currency_symbol", config.DEFAULT_CURRENCY_SYMBOL)
    return conn, symbol
