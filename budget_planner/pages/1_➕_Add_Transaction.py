"""Add Transaction page."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

import database as db
import db_session
import theme

theme.apply('Add Transaction', '➕', subtitle='Log money in or out.')

conn, symbol = db_session.get_conn_and_sync()


tx_type = st.radio("Type", ["Expense", "Income"], horizontal=True)
categories_df = db.get_categories(conn, kind=tx_type)

if categories_df.empty:
    st.warning(f"No {tx_type.lower()} categories yet. Add one on the Settings page.")
else:
    cat_options = [f"{row['icon']} {row['name']}" for _, row in categories_df.iterrows()]
    cat_names = categories_df["name"].tolist()

    goals_df = db.get_goals(conn)
    link_goal = tx_type == "Expense" and not goals_df.empty

    with st.form("add_tx_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tx_date = c1.date_input("Date", value=date.today())
        choice = c2.selectbox("Category", cat_options)
        category = cat_names[cat_options.index(choice)]
        amount = st.number_input(f"Amount ({symbol})", min_value=0.01, step=1.0, format="%.2f")
        note = st.text_input("Note (optional)")

        goal_id = None
        if link_goal:
            goal_names = goals_df["name"].tolist()
            goal_choice = st.selectbox("Contribute to a goal? (optional)", ["None"] + goal_names)
            if goal_choice != "None":
                goal_id = int(goals_df.loc[goals_df["name"] == goal_choice, "id"].iloc[0])

        submitted = st.form_submit_button("Add Transaction", width="stretch")

        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                db.add_transaction(conn, tx_date, tx_type, category, amount, note, goal_id=goal_id)
                st.success(f"Added {tx_type.lower()}: {symbol}{amount:,.2f} in {category}")
                st.rerun()

st.divider()
st.caption("Need a new category? Add it on the ⚙️ Settings page first.")
