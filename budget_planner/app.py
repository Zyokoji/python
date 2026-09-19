"""
Budget Planner — Overview
Run with: streamlit run app.py
"""

from datetime import date

import pandas as pd
import streamlit as st

import database as db
import db_session
import theme
import utils

today = date.today()
theme.apply("Overview", "💰", subtitle=today.strftime("%B %Y"))

conn, symbol = db_session.get_conn_and_sync()

month_start, month_end = utils.month_bounds(today)
df_month = db.get_transactions(conn, start_date=month_start, end_date=month_end)

income = float(df_month.loc[df_month["type"] == "Income", "amount"].sum())
expenses = float(df_month.loc[df_month["type"] == "Expense", "amount"].sum())
net = income - expenses
savings_rate = (net / income * 100) if income > 0 else None

theme.stat_row(
    [
        {"label": "Money in", "value": utils.format_currency(income, symbol), "tone": "pos"},
        {"label": "Money out", "value": utils.format_currency(expenses, symbol), "tone": "neg"},
        {
            "label": "Net",
            "value": utils.format_currency(net, symbol),
            "tone": "pos" if net >= 0 else "neg",
        },
        {
            "label": "Saved",
            "value": f"{savings_rate:.0f}%" if savings_rate is not None else "—",
            "tone": "" if savings_rate is None else ("pos" if savings_rate >= 0 else "neg"),
            "note": "of income this month" if savings_rate is not None else "no income logged yet",
        },
    ]
)

expense_df = df_month[df_month["type"] == "Expense"]
left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("Where the money went")
    if expense_df.empty:
        theme.empty_note("No expenses logged this month yet. Add one from the Add Transaction page.")
    else:
        by_cat = expense_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        st.bar_chart(by_cat, color=theme.chart_colors()["accent"], height=260)

    st.subheader("In and out, last six months")
    trend_df = db.get_transactions(conn, start_date=utils.months_ago(today, 5))
    if trend_df.empty:
        theme.empty_note("Once you have a couple of months of history, the trend shows up here.")
    else:
        trend_df = trend_df.copy()
        trend_df["month"] = trend_df["date"].apply(lambda d: d.strftime("%Y-%m"))
        pivot = trend_df.pivot_table(
            index="month", columns="type", values="amount", aggfunc="sum", fill_value=0
        )
        for col in ("Income", "Expense"):
            if col not in pivot.columns:
                pivot[col] = 0
        pivot = pivot[["Income", "Expense"]]
        cc = theme.chart_colors()
        st.line_chart(pivot, color=[cc["positive"], cc["negative"]], height=260)

with right:
    st.subheader("Budgets")
    budgets_df = db.get_budgets(conn)
    if budgets_df.empty:
        theme.empty_note("No limits set yet. Set one on the Budgets page to track pacing.")
    else:
        spend_by_cat = (
            expense_df.groupby("category")["amount"].sum() if not expense_df.empty else pd.Series(dtype=float)
        )
        for _, row in budgets_df.iterrows():
            spent = float(spend_by_cat.get(row["category"], 0.0))
            limit_amt = float(row["monthly_limit"])
            pct = min(spent / limit_amt, 1.0) if limit_amt > 0 else 0.0
            st.progress(
                pct,
                text=f"{row['category']} · {utils.format_currency(spent, symbol)} of {utils.format_currency(limit_amt, symbol)}",
            )
            if limit_amt > 0:
                pace = utils.budget_pace(spent, limit_amt, today)
                if not pace["on_track"]:
                    theme.caption(
                        f"On pace for {utils.format_currency(pace['projected_total'], symbol)} by month end",
                        tone="neg",
                    )

    st.subheader("Coming up")
    recurring_df = db.get_recurring(conn, active_only=True)
    if recurring_df.empty:
        theme.empty_note("Add rent, subscriptions or a paycheck on the Recurring page and they post themselves.")
    else:
        for _, row in recurring_df.head(5).iterrows():
            theme.line_item(
                row["name"],
                utils.format_currency(row["amount"], symbol),
                meta=row["next_date"].strftime("%a %d %b"),
                tone="pos" if row["type"] == "Income" else "neg",
            )

    st.subheader("Goals")
    goals_df = db.get_goals(conn)
    if goals_df.empty:
        theme.empty_note("Set a savings target on the Goals page to track it here.")
    else:
        for _, row in goals_df.iterrows():
            progress = db.get_goal_progress(conn, int(row["id"]))
            target = float(row["target_amount"])
            pct = min(progress / target, 1.0) if target else 0.0
            st.progress(
                pct,
                text=f"{row['name']} · {utils.format_currency(progress, symbol)} of {utils.format_currency(target, symbol)}",
            )
