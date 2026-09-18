"""
Budget Planner — Home / Overview
Run with: streamlit run app.py
"""

from datetime import date

import pandas as pd
import streamlit as st

import database as db
import db_session
import utils

st.set_page_config(page_title="Budget Planner", page_icon="💰", layout="wide")

conn, symbol = db_session.get_conn_and_sync()

st.title("💰 Budget Planner")

today = date.today()
month_start, month_end = utils.month_bounds(today)
df_month = db.get_transactions(conn, start_date=month_start, end_date=month_end)

income = df_month.loc[df_month["type"] == "Income", "amount"].sum()
expenses = df_month.loc[df_month["type"] == "Expense", "amount"].sum()
net = income - expenses
savings_rate = (net / income * 100) if income > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Income this month", utils.format_currency(income, symbol))
col2.metric("Expenses this month", utils.format_currency(expenses, symbol))
col3.metric("Net", utils.format_currency(net, symbol))
col4.metric("Savings rate", f"{savings_rate:.0f}%" if income > 0 else "—")

expense_df = df_month[df_month["type"] == "Expense"]

left, right = st.columns([3, 2])

with left:
    st.subheader("Spending by Category")
    if expense_df.empty:
        st.caption("No expenses recorded yet this month.")
    else:
        by_cat = expense_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        st.bar_chart(by_cat)

    st.subheader("Income vs. Expenses (last 6 months)")
    six_months_ago = utils.months_ago(today, 5)
    trend_df = db.get_transactions(conn, start_date=six_months_ago)
    if trend_df.empty:
        st.caption("Not enough history yet.")
    else:
        trend_df = trend_df.copy()
        trend_df["month"] = trend_df["date"].apply(lambda d: d.strftime("%Y-%m"))
        pivot = trend_df.pivot_table(
            index="month", columns="type", values="amount", aggfunc="sum", fill_value=0
        )
        st.line_chart(pivot)

with right:
    st.subheader("Budget Status")
    budgets_df = db.get_budgets(conn)
    if budgets_df.empty:
        st.caption("No budgets set yet. Head to the Budgets page to set monthly limits.")
    else:
        spend_by_cat = expense_df.groupby("category")["amount"].sum() if not expense_df.empty else pd.Series(dtype=float)
        for _, row in budgets_df.iterrows():
            spent = float(spend_by_cat.get(row["category"], 0.0))
            limit_amt = row["monthly_limit"]
            pct = min(spent / limit_amt, 1.0) if limit_amt > 0 else 0.0
            st.progress(
                pct,
                text=f"{row['category']}: {utils.format_currency(spent, symbol)} / {utils.format_currency(limit_amt, symbol)}",
            )
            if limit_amt > 0:
                pace = utils.budget_pace(spent, limit_amt, today)
                if not pace["on_track"]:
                    st.caption(f"⚠️ On pace for {utils.format_currency(pace['projected_total'], symbol)} by month end")

    st.subheader("Upcoming Recurring")
    recurring_df = db.get_recurring(conn, active_only=True)
    if recurring_df.empty:
        st.caption("No recurring transactions set up.")
    else:
        for _, row in recurring_df.head(5).iterrows():
            st.write(f"**{row['name']}** — {utils.format_currency(row['amount'], symbol)} on {row['next_date'].strftime('%b %d')}")

    st.subheader("Savings Goals")
    goals_df = db.get_goals(conn)
    if goals_df.empty:
        st.caption("No goals yet. Add one on the Goals page.")
    else:
        for _, row in goals_df.iterrows():
            progress = db.get_goal_progress(conn, row["id"])
            pct = min(progress / row["target_amount"], 1.0) if row["target_amount"] else 0.0
            st.progress(
                pct,
                text=f"{row['name']}: {utils.format_currency(progress, symbol)} / {utils.format_currency(row['target_amount'], symbol)}",
            )

st.divider()
st.caption("Use the sidebar to add transactions, manage budgets, recurring bills, goals, and settings.")
