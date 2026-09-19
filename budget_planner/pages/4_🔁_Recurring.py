"""Recurring transactions — bills and income that repeat on a schedule."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

import config
import database as db
import db_session
import theme
import utils

theme.apply('Recurring', '🔁', subtitle='Bills and income that repeat. These post themselves when you open the app.')

conn, symbol = db_session.get_conn_and_sync()

st.caption("Recurring items are generated automatically whenever you open the app.")

st.subheader("Add a repeating item")
tx_type = st.radio("Type", ["Expense", "Income"], horizontal=True, key="recurring_type")
categories_df = db.get_categories(conn, kind=tx_type)

if categories_df.empty:
    st.warning(f"No {tx_type.lower()} categories yet. Add one on the Settings page.")
else:
    with st.form("recurring_form", clear_on_submit=True):
        name = st.text_input("Name (e.g. Rent, Netflix, Paycheck)")
        c1, c2, c3 = st.columns(3)
        category = c1.selectbox("Category", categories_df["name"].tolist())
        amount = c2.number_input(f"Amount ({symbol})", min_value=0.01, step=1.0, format="%.2f")
        frequency = c3.selectbox("Frequency", config.FREQUENCIES, index=config.FREQUENCIES.index("Monthly"))
        start_date = st.date_input("First occurrence", value=date.today())
        submitted = st.form_submit_button("Add Recurring Transaction")

        if submitted:
            if not name.strip():
                st.error("Please give it a name.")
            else:
                db.add_recurring(conn, name.strip(), tx_type, category, amount, frequency, start_date)
                st.success(f"Added recurring {tx_type.lower()}: {name}")
                st.rerun()

st.divider()
st.subheader("Your repeating items")
recurring_df = db.get_recurring(conn)

if recurring_df.empty:
    theme.empty_note("Nothing repeating yet. Add rent, a subscription or a paycheck above.")
else:
    for _, row in recurring_df.iterrows():
        c1, c2, c3, c4 = st.columns([3, 3, 1, 1])
        status = "🟢 Active" if row["active"] else "⏸️ Paused"
        c1.write(f"**{row['name']}** ({row['category']})")
        c2.write(
            f"{utils.format_currency(row['amount'], symbol)} — {row['frequency']}, "
            f"next {row['next_date'].strftime('%b %d, %Y')}"
        )
        c3.write(status)
        toggle_label = "Pause" if row["active"] else "Resume"
        if c4.button(toggle_label, key=f"toggle_{row['id']}"):
            db.set_recurring_active(conn, int(row["id"]), not bool(row["active"]))
            st.rerun()

    st.divider()
    to_delete = st.selectbox(
        "Remove a recurring transaction",
        ["None"] + [f"{row['id']} — {row['name']}" for _, row in recurring_df.iterrows()],
    )
    if to_delete != "None" and st.button("🗑️ Delete Selected", type="secondary"):
        rec_id = int(to_delete.split(" — ")[0])
        db.delete_recurring(conn, rec_id)
        st.success("Deleted.")
        st.rerun()

    if st.button("🔄 Process recurring now"):
        count = db.process_recurring(conn)
        st.success(f"Generated {count} transaction{'s' if count != 1 else ''}." if count else "Nothing due yet.")
        st.rerun()
