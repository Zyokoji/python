"""Budgets — set monthly limits per expense category and see pacing."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

import database as db
import db_session
import utils

st.set_page_config(page_title="Budgets", page_icon="🎯", layout="wide")
conn, symbol = db_session.get_conn_and_sync()

st.title("🎯 Budgets")

expense_categories = db.get_categories(conn, kind="Expense")
budgets_df = db.get_budgets(conn)
existing = dict(zip(budgets_df["category"], budgets_df["monthly_limit"])) if not budgets_df.empty else {}

st.subheader("Set a Monthly Limit")
if expense_categories.empty:
    st.warning("No expense categories yet. Add one on the Settings page.")
else:
    with st.form("budget_form"):
        c1, c2 = st.columns([2, 1])
        category = c1.selectbox("Category", expense_categories["name"].tolist())
        limit_amount = c2.number_input(
            f"Monthly limit ({symbol})",
            min_value=0.0,
            step=10.0,
            value=float(existing.get(category, 0.0)),
            format="%.2f",
        )
        save = st.form_submit_button("Save Budget")
        if save:
            db.set_budget(conn, category, limit_amount)
            st.success(f"Budget for {category} set to {utils.format_currency(limit_amount, symbol)}")
            st.rerun()

st.divider()
st.subheader("This Month's Status")

today = date.today()
month_start, month_end = utils.month_bounds(today)
df_month = db.get_transactions(conn, start_date=month_start, end_date=month_end, tx_type="Expense")
spend_by_cat = df_month.groupby("category")["amount"].sum() if not df_month.empty else {}

if budgets_df.empty:
    st.caption("No budgets set yet — add one above.")
else:
    total_limit = budgets_df["monthly_limit"].sum()
    total_spent = sum(float(spend_by_cat.get(cat, 0.0)) for cat in budgets_df["category"])
    st.metric(
        "Total budgeted vs. spent",
        f"{utils.format_currency(total_spent, symbol)} / {utils.format_currency(total_limit, symbol)}",
    )

    for _, row in budgets_df.sort_values("category").iterrows():
        spent = float(spend_by_cat.get(row["category"], 0.0))
        limit_amt = row["monthly_limit"]
        pct = min(spent / limit_amt, 1.0) if limit_amt > 0 else 0.0

        cols = st.columns([4, 1])
        cols[0].progress(
            pct,
            text=f"{row['category']} — {utils.format_currency(spent, symbol)} / {utils.format_currency(limit_amt, symbol)}",
        )
        if cols[1].button("Remove", key=f"remove_{row['category']}"):
            db.delete_budget(conn, row["category"])
            st.rerun()

        if limit_amt > 0:
            pace = utils.budget_pace(spent, limit_amt, today)
            if pace["on_track"]:
                st.caption(
                    f"✅ On track — about {utils.format_currency(pace['daily_allowance'], symbol)}/day left to stay under budget."
                )
            else:
                over_by = pace["projected_total"] - limit_amt
                st.caption(
                    f"⚠️ On pace to reach {utils.format_currency(pace['projected_total'], symbol)} by month end — "
                    f"over by {utils.format_currency(over_by, symbol)}."
                )
