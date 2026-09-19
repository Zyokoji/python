"""Savings goals — set a target and track contributions."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

import database as db
import db_session
import theme
import utils

theme.apply('Goals', '🏆', subtitle='Set a target, track contributions towards it.')

conn, symbol = db_session.get_conn_and_sync()


st.subheader("New goal")
with st.form("goal_form", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    name = c1.text_input("Goal name (e.g. Emergency Fund)")
    target_amount = c2.number_input(f"Target amount ({symbol})", min_value=0.01, step=50.0, format="%.2f")
    target_date = c3.date_input("Target date (optional)", value=None)
    submitted = st.form_submit_button("Create Goal")
    if submitted:
        if not name.strip():
            st.error("Please name your goal.")
        else:
            db.add_goal(conn, name.strip(), target_amount, target_date)
            st.success(f"Created goal: {name}")
            st.rerun()

st.divider()
goals_df = db.get_goals(conn)

if goals_df.empty:
    theme.empty_note("No goals yet. Name a target above and contributions will track against it.")
else:
    for _, row in goals_df.iterrows():
        progress = db.get_goal_progress(conn, row["id"])
        pct = min(progress / row["target_amount"], 1.0) if row["target_amount"] else 0.0

        st.subheader(row["name"])
        st.progress(
            pct,
            text=f"{utils.format_currency(progress, symbol)} of {utils.format_currency(row['target_amount'], symbol)}",
        )

        monthly_rate = db.get_goal_monthly_rate(conn, row["id"])
        st.caption(utils.project_goal_completion(progress, row["target_amount"], monthly_rate))
        if pd.notna(row["target_date"]):
            st.caption(f"Target date: {row['target_date'].strftime('%b %d, %Y')}")

        with st.expander(f"Add a contribution to {row['name']}"):
            with st.form(f"contribute_{row['id']}", clear_on_submit=True):
                amount = st.number_input(
                    f"Amount ({symbol})", min_value=0.01, step=10.0, format="%.2f", key=f"amt_{row['id']}"
                )
                note = st.text_input("Note (optional)", key=f"note_{row['id']}")
                contribute = st.form_submit_button("Add Contribution")
                if contribute:
                    db.add_transaction(
                        conn,
                        date.today(),
                        "Expense",
                        "Savings",
                        amount,
                        note=note or f"Contribution to {row['name']}",
                        goal_id=int(row["id"]),
                    )
                    st.success(f"Added {utils.format_currency(amount, symbol)} to {row['name']}")
                    st.rerun()

        if st.button(f"Archive '{row['name']}'", key=f"archive_{row['id']}"):
            db.archive_goal(conn, int(row["id"]))
            st.rerun()

        st.divider()
