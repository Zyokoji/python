"""Transaction History — filter, edit, delete, export."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

import database as db
import db_session
import utils

st.set_page_config(page_title="History", page_icon="📜", layout="wide")
conn, symbol = db_session.get_conn_and_sync()

st.title("📜 Transaction History")

with st.expander("Filters", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    default_start = utils.months_ago(date.today(), 2)
    start = c1.date_input("From", value=default_start)
    end = c2.date_input("To", value=date.today())
    tx_type_filter = c3.selectbox("Type", ["All", "Income", "Expense"])
    all_categories = db.get_categories(conn, include_archived=True)["name"].tolist()
    category_filter = c4.selectbox("Category", ["All"] + all_categories)
    search = st.text_input("Search notes/category")

df = db.get_transactions(
    conn,
    start_date=start,
    end_date=end,
    category=None if category_filter == "All" else category_filter,
    tx_type=None if tx_type_filter == "All" else tx_type_filter,
    search=search or None,
)

if df.empty:
    st.info("No transactions match these filters.")
else:
    total_in = df.loc[df["type"] == "Income", "amount"].sum()
    total_out = df.loc[df["type"] == "Expense", "amount"].sum()
    st.write(
        f"{len(df)} transaction{'s' if len(df) != 1 else ''} — "
        f"{utils.format_currency(total_in, symbol)} in, {utils.format_currency(total_out, symbol)} out"
    )

    display_df = df[["id", "date", "type", "category", "amount", "note"]].copy()
    st.dataframe(display_df, width="stretch", hide_index=True)

    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, "transactions.csv", "text/csv")

    st.divider()
    st.subheader("Edit or Delete a Transaction")
    id_options = df["id"].tolist()
    selected_id = st.selectbox(
        "Select by ID",
        id_options,
        format_func=lambda i: (
            f"#{i} — {df.loc[df['id'] == i, 'date'].iloc[0]} — "
            f"{df.loc[df['id'] == i, 'category'].iloc[0]} — "
            f"{symbol}{df.loc[df['id'] == i, 'amount'].iloc[0]:,.2f}"
        ),
    )
    row = df.loc[df["id"] == selected_id].iloc[0]

    edit_categories = db.get_categories(conn, kind=row["type"], include_archived=True)
    cat_names = edit_categories["name"].tolist()
    if row["category"] not in cat_names:
        cat_names = [row["category"]] + cat_names  # keep an archived/legacy category selectable

    with st.form("edit_tx_form"):
        c1, c2 = st.columns(2)
        new_date = c1.date_input("Date", value=row["date"])
        new_type = c2.selectbox("Type", ["Expense", "Income"], index=["Expense", "Income"].index(row["type"]))
        new_category = st.selectbox("Category", cat_names, index=cat_names.index(row["category"]))
        new_amount = st.number_input("Amount", min_value=0.01, value=float(row["amount"]), step=1.0, format="%.2f")
        new_note = st.text_input("Note", value=row["note"] or "")

        col_a, col_b = st.columns(2)
        save = col_a.form_submit_button("💾 Save Changes", width="stretch")
        delete = col_b.form_submit_button("🗑️ Delete", width="stretch", type="secondary")

        if save:
            db.update_transaction(
                conn,
                int(selected_id),
                date=new_date,
                type=new_type,
                category=new_category,
                amount=new_amount,
                note=new_note,
            )
            st.success(f"Updated transaction #{selected_id}")
            st.rerun()

        if delete:
            db.delete_transaction(conn, int(selected_id))
            st.success(f"Deleted transaction #{selected_id}")
            st.rerun()
