"""Settings — manage categories, currency, and backup/restore your data."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

import config
import database as db
import db_session
import theme

theme.apply('Settings', '⚙️', subtitle='Categories, currency, and your data.')

conn, symbol = db_session.get_conn_and_sync()


# --- Currency ---------------------------------------------------------------
st.subheader("Currency")
labels = list(config.CURRENCY_OPTIONS.keys()) + ["Custom"]
current_label = next((k for k, v in config.CURRENCY_OPTIONS.items() if v == symbol), "Custom")
choice = st.selectbox("Currency symbol", labels, index=labels.index(current_label))
if choice == "Custom":
    new_symbol = st.text_input("Custom symbol", value=symbol, max_chars=3)
else:
    new_symbol = config.CURRENCY_OPTIONS[choice]
if st.button("Save Currency"):
    db.set_setting(conn, "currency_symbol", new_symbol or "$")
    st.success(f"Currency symbol set to {new_symbol}")
    st.rerun()

st.divider()

# --- Categories ---------------------------------------------------------------
st.subheader("Categories")
tab_income, tab_expense = st.tabs(["Income Categories", "Expense Categories"])

for tab, kind in [(tab_income, "Income"), (tab_expense, "Expense")]:
    with tab:
        cats = db.get_categories(conn, kind=kind, include_archived=True)
        for _, row in cats.iterrows():
            c1, c2 = st.columns([4, 1])
            label = f"{row['icon']} {row['name']}" + (" (archived)" if row["archived"] else "")
            c1.write(label)
            btn_label = "Restore" if row["archived"] else "Archive"
            if c2.button(btn_label, key=f"{kind}_{row['name']}"):
                db.set_category_archived(conn, row["name"], not bool(row["archived"]))
                st.rerun()

        with st.form(f"add_category_{kind}", clear_on_submit=True):
            st.write(f"Add a new {kind.lower()} category")
            c1, c2 = st.columns([3, 1])
            new_name = c1.text_input("Name", key=f"name_{kind}")
            new_icon = c2.text_input("Icon (emoji)", value="🏷️", key=f"icon_{kind}", max_chars=4)
            if st.form_submit_button("Add Category"):
                if not new_name.strip():
                    st.error("Category name can't be empty.")
                else:
                    db.add_category(conn, new_name.strip(), kind, new_icon.strip() or "🏷️")
                    st.success(f"Added category: {new_name}")
                    st.rerun()

st.divider()

# --- Backup / Restore ---------------------------------------------------------
st.subheader("Backup and restore")
c1, c2 = st.columns(2)

with c1:
    st.write("**Export**")
    export_payload = db.export_data(conn)
    backup_json = json.dumps(export_payload, indent=2, default=str)
    st.download_button(
        "⬇️ Download backup (JSON)",
        backup_json,
        file_name=f"budget_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )

with c2:
    st.write("**Restore**")
    uploaded = st.file_uploader("Upload a backup JSON file", type="json")
    replace = st.checkbox("Replace all existing data (instead of merging)", value=False)
    if st.button("Restore Backup"):
        if uploaded is None:
            st.error("Please upload a backup file first.")
        else:
            try:
                restored = json.loads(uploaded.read().decode("utf-8"))
                db.import_data(conn, restored, replace=replace)
                st.success("Backup restored.")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't restore backup: {e}")

st.divider()
st.subheader("Erase everything")
with st.expander("Reset all data"):
    st.warning("This permanently deletes every transaction, budget, recurring item, and goal.")
    confirm_text = st.text_input("Type RESET to confirm")
    if st.button("Erase Everything", type="secondary"):
        if confirm_text == "RESET":
            db.import_data(conn, {}, replace=True)
            db.seed_defaults(conn)
            st.success("All data cleared.")
            st.rerun()
        else:
            st.error("Type RESET (all caps) in the box above to confirm.")
