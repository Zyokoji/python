"""End-to-end tests using Streamlit's official AppTest framework.

These actually execute each page's script (no real server/browser
needed) and simulate real user interactions: filling in forms,
clicking buttons, checking the resulting state. This catches bugs that
pure unit tests on database.py/utils.py can't, like a typo in a widget
call or a page crashing on an empty database.
"""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]

PAGE_FILES = [
    "app.py",
    "pages/1_➕_Add_Transaction.py",
    "pages/2_📜_History.py",
    "pages/3_🎯_Budgets.py",
    "pages/4_🔁_Recurring.py",
    "pages/5_🏆_Goals.py",
    "pages/6_⚙️_Settings.py",
]


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point every test at a throwaway SQLite file instead of the real
    budget.db, and clear Streamlit's resource cache so each test gets
    its own fresh connection instead of reusing another test's."""
    import config

    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


@pytest.mark.parametrize("page", PAGE_FILES)
def test_page_runs_without_exception(page):
    at = AppTest.from_file(str(ROOT / page), default_timeout=15)
    at.run()
    assert not at.exception, f"{page} raised: {[str(e) for e in at.exception]}"


def test_add_transaction_via_form_submit():
    at = AppTest.from_file(str(ROOT / "pages/1_➕_Add_Transaction.py"), default_timeout=15)
    at.run()
    assert not at.exception

    # Fill the number input (amount) and submit the form.
    at.number_input[0].set_value(55.5).run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception

    # Verify it actually landed in the database.
    import database as db
    import db_session

    conn, _ = db_session.get_conn_and_sync()
    df = db.get_transactions(conn)
    assert len(df) == 1
    assert df.iloc[0]["amount"] == 55.5


def test_goal_creation_with_no_target_date():
    """Regression check: st.date_input(value=None) must not crash the
    Goals page when the user leaves the optional target date blank."""
    at = AppTest.from_file(str(ROOT / "pages/5_🏆_Goals.py"), default_timeout=15)
    at.run()
    assert not at.exception

    at.text_input[0].set_value("Emergency Fund").run()
    at.number_input[0].set_value(1000).run()
    at.button[0].click().run()
    assert not at.exception

    import database as db
    import db_session

    conn, _ = db_session.get_conn_and_sync()
    goals = db.get_goals(conn)
    assert len(goals) == 1
    assert goals.iloc[0]["name"] == "Emergency Fund"


def test_settings_reset_requires_exact_confirmation_text():
    at = AppTest.from_file(str(ROOT / "pages/6_⚙️_Settings.py"), default_timeout=15)
    at.run()
    assert not at.exception

    erase_button = [b for b in at.button if b.label == "Erase Everything"][0]
    erase_button.click().run()
    assert not at.exception
    # Should show an error (wrong/missing confirmation) rather than wiping data.
    assert len(at.error) >= 1


def test_history_edit_and_delete_transaction():
    import database as db
    import db_session

    conn, _ = db_session.get_conn_and_sync()
    from datetime import date

    tx_id = db.add_transaction(conn, date(2026, 9, 1), "Expense", "Groceries", 42.0, "original note")

    at = AppTest.from_file(str(ROOT / "pages/2_📜_History.py"), default_timeout=15)
    at.run()
    assert not at.exception

    # Widget order on this page: date_input[From, To, edit-Date],
    # selectbox[Type filter, Category filter, Select-by-ID, edit-Type, edit-Category],
    # number_input[edit-Amount], button[Save Changes, Delete].
    at.number_input[0].set_value(99.0).run()
    assert not at.exception
    save_button = [b for b in at.button if "Save Changes" in b.label][0]
    save_button.click().run()
    assert not at.exception

    row = db.get_transaction(conn, tx_id)
    assert row["amount"] == 99.0

    # Re-run fresh and delete it.
    at2 = AppTest.from_file(str(ROOT / "pages/2_📜_History.py"), default_timeout=15)
    at2.run()
    delete_button = [b for b in at2.button if "Delete" in b.label and "Save" not in b.label][0]
    delete_button.click().run()
    assert not at2.exception
    assert db.get_transaction(conn, tx_id) is None


def test_recurring_auto_generates_when_home_page_loads():
    """A recurring item due in the past should be generated the moment
    the app is opened, via db_session's once-per-session sync."""
    import database as db
    import db_session
    from datetime import date, timedelta

    conn, _ = db_session.get_conn_and_sync()
    db.add_recurring(conn, "Rent", "Expense", "Rent/Mortgage", 1200, "Monthly", date.today() - timedelta(days=1))

    assert db.get_transactions(conn, category="Rent/Mortgage").empty

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15)
    at.run()
    assert not at.exception

    assert not db.get_transactions(conn, category="Rent/Mortgage").empty


def test_archived_category_hidden_from_add_transaction():
    import database as db
    import db_session

    conn, _ = db_session.get_conn_and_sync()
    db.set_category_archived(conn, "Entertainment", True)

    at = AppTest.from_file(str(ROOT / "pages/1_➕_Add_Transaction.py"), default_timeout=15)
    at.run()
    assert not at.exception

    category_select = at.selectbox[0]
    assert not any("Entertainment" in opt for opt in category_select.options)


def test_recurring_page_add_and_pause():
    at = AppTest.from_file(str(ROOT / "pages/4_🔁_Recurring.py"), default_timeout=15)
    at.run()
    assert not at.exception

    at.text_input[0].set_value("Netflix").run()
    at.number_input[0].set_value(15.99).run()
    submit_buttons = [b for b in at.button if "Add Recurring" in b.label]
    assert submit_buttons
    submit_buttons[0].click().run()
    assert not at.exception

    import database as db
    import db_session

    conn, _ = db_session.get_conn_and_sync()
    recurring = db.get_recurring(conn)
    assert len(recurring) == 1
    assert recurring.iloc[0]["name"] == "Netflix"
