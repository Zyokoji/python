import sqlite3
from datetime import date

import pandas as pd
import pytest

import database as db


@pytest.fixture
def conn():
    connection = db.get_connection(":memory:")
    yield connection
    connection.close()


# --------------------------------------------------------------------------- #
# Schema / categories
# --------------------------------------------------------------------------- #


def test_schema_seeds_default_categories(conn):
    cats = db.get_categories(conn)
    names = set(cats["name"])
    assert "Groceries" in names
    assert "Salary" in names


def test_category_archive_hides_from_default_list(conn):
    db.add_category(conn, "Pet Care", "Expense", "🐾")
    assert "Pet Care" in set(db.get_categories(conn)["name"])
    db.set_category_archived(conn, "Pet Care", True)
    assert "Pet Care" not in set(db.get_categories(conn)["name"])
    assert "Pet Care" in set(db.get_categories(conn, include_archived=True)["name"])


def test_add_category_rejects_empty_name(conn):
    with pytest.raises(ValueError):
        db.add_category(conn, "   ", "Expense")


def test_add_category_rejects_bad_kind(conn):
    with pytest.raises(ValueError):
        db.add_category(conn, "Whatever", "Neither")


# --------------------------------------------------------------------------- #
# Transactions
# --------------------------------------------------------------------------- #


def test_add_and_get_transaction(conn):
    tx_id = db.add_transaction(conn, date(2026, 9, 1), "Expense", "Groceries", 42.50, "Weekly shop")
    df = db.get_transactions(conn)
    assert len(df) == 1
    assert df.iloc[0]["amount"] == 42.50
    assert df.iloc[0]["id"] == tx_id
    assert df.iloc[0]["date"] == date(2026, 9, 1)


def test_add_transaction_rejects_non_positive_amount(conn):
    with pytest.raises(ValueError):
        db.add_transaction(conn, date.today(), "Expense", "Groceries", 0)
    with pytest.raises(ValueError):
        db.add_transaction(conn, date.today(), "Expense", "Groceries", -5)


def test_add_transaction_rejects_bad_type(conn):
    with pytest.raises(ValueError):
        db.add_transaction(conn, date.today(), "Nope", "Groceries", 10)


def test_add_transaction_rejects_unknown_category(conn):
    with pytest.raises(sqlite3.IntegrityError):
        db.add_transaction(conn, date.today(), "Expense", "Not A Real Category", 10)


def test_update_transaction(conn):
    tx_id = db.add_transaction(conn, date(2026, 9, 1), "Expense", "Groceries", 10, "old note")
    db.update_transaction(conn, tx_id, amount=20, note="new note")
    row = db.get_transaction(conn, tx_id)
    assert row["amount"] == 20
    assert row["note"] == "new note"


def test_update_transaction_rejects_bad_amount(conn):
    tx_id = db.add_transaction(conn, date.today(), "Expense", "Groceries", 10)
    with pytest.raises(ValueError):
        db.update_transaction(conn, tx_id, amount=-5)


def test_update_transaction_rejects_unknown_field(conn):
    tx_id = db.add_transaction(conn, date.today(), "Expense", "Groceries", 10)
    with pytest.raises(ValueError):
        db.update_transaction(conn, tx_id, id=999)


def test_delete_transaction(conn):
    tx_id = db.add_transaction(conn, date.today(), "Expense", "Groceries", 10)
    db.delete_transaction(conn, tx_id)
    assert db.get_transaction(conn, tx_id) is None


def test_get_transactions_filters(conn):
    db.add_transaction(conn, date(2026, 1, 15), "Expense", "Groceries", 10)
    db.add_transaction(conn, date(2026, 2, 15), "Income", "Salary", 1000)

    df = db.get_transactions(conn, tx_type="Income")
    assert len(df) == 1
    assert df.iloc[0]["category"] == "Salary"

    df2 = db.get_transactions(conn, start_date=date(2026, 2, 1))
    assert len(df2) == 1
    assert df2.iloc[0]["category"] == "Salary"

    df3 = db.get_transactions(conn, search="sala")
    assert len(df3) == 1


def test_get_transactions_empty_has_expected_columns(conn):
    df = db.get_transactions(conn)
    assert df.empty
    assert "amount" in df.columns
    assert "type" in df.columns


# --------------------------------------------------------------------------- #
# Budgets
# --------------------------------------------------------------------------- #


def test_budget_set_and_get(conn):
    db.set_budget(conn, "Groceries", 400)
    budgets = db.get_budgets(conn)
    assert budgets.loc[budgets["category"] == "Groceries", "monthly_limit"].iloc[0] == 400
    db.set_budget(conn, "Groceries", 450)  # upsert
    budgets = db.get_budgets(conn)
    assert budgets.loc[budgets["category"] == "Groceries", "monthly_limit"].iloc[0] == 450


def test_budget_rejects_negative(conn):
    with pytest.raises(ValueError):
        db.set_budget(conn, "Groceries", -10)


def test_delete_budget(conn):
    db.set_budget(conn, "Groceries", 400)
    db.delete_budget(conn, "Groceries")
    assert db.get_budgets(conn).empty


# --------------------------------------------------------------------------- #
# Recurring transactions
# --------------------------------------------------------------------------- #


def test_recurring_generates_due_transactions(conn):
    rec_id = db.add_recurring(conn, "Rent", "Expense", "Rent/Mortgage", 1500, "Monthly", date(2026, 1, 1))
    generated = db.process_recurring(conn, as_of=date(2026, 3, 15))
    # Jan 1, Feb 1, Mar 1 should all have fired
    assert generated == 3
    df = db.get_transactions(conn, category="Rent/Mortgage")
    assert len(df) == 3
    rec = db.get_recurring(conn)
    next_date = rec.loc[rec["id"] == rec_id, "next_date"].iloc[0]
    assert next_date == date(2026, 4, 1)


def test_recurring_month_end_rollover(conn):
    # Jan 31 monthly should land on Feb 28 in 2026 (not a leap year), no crash
    db.add_recurring(conn, "Subscription", "Expense", "Subscriptions", 9.99, "Monthly", date(2026, 1, 31))
    db.process_recurring(conn, as_of=date(2026, 3, 1))
    df = db.get_transactions(conn, category="Subscriptions")
    dates = sorted(df["date"].tolist())
    assert dates == [date(2026, 1, 31), date(2026, 2, 28)]


def test_recurring_leap_year_yearly(conn):
    db.add_recurring(conn, "Anniversary gift", "Expense", "Other", 50, "Yearly", date(2024, 2, 29))
    db.process_recurring(conn, as_of=date(2026, 6, 1))
    df = db.get_transactions(conn, category="Other")
    dates = sorted(df["date"].tolist())
    # 2024-02-29, then non-leap years fall back to the 28th
    assert dates == [date(2024, 2, 29), date(2025, 2, 28), date(2026, 2, 28)]


def test_recurring_inactive_not_processed(conn):
    rec_id = db.add_recurring(conn, "Old thing", "Expense", "Other", 5, "Monthly", date(2020, 1, 1))
    db.set_recurring_active(conn, rec_id, False)
    generated = db.process_recurring(conn, as_of=date(2026, 9, 16))
    assert generated == 0


def test_recurring_not_yet_due_generates_nothing(conn):
    db.add_recurring(conn, "Future thing", "Expense", "Other", 5, "Monthly", date(2030, 1, 1))
    generated = db.process_recurring(conn, as_of=date(2026, 9, 16))
    assert generated == 0


def test_delete_recurring_nulls_transaction_link(conn):
    rec_id = db.add_recurring(conn, "Rent", "Expense", "Rent/Mortgage", 1000, "Monthly", date(2026, 1, 1))
    db.process_recurring(conn, as_of=date(2026, 1, 1))
    df = db.get_transactions(conn, category="Rent/Mortgage")
    assert df.iloc[0]["recurring_id"] == rec_id

    db.delete_recurring(conn, rec_id)
    df2 = db.get_transactions(conn, category="Rent/Mortgage")
    assert pd.isna(df2.iloc[0]["recurring_id"])


# --------------------------------------------------------------------------- #
# Goals
# --------------------------------------------------------------------------- #


def test_goal_progress(conn):
    goal_id = db.add_goal(conn, "Emergency Fund", 1000, date(2027, 1, 1))
    db.add_transaction(conn, date(2026, 7, 15), "Expense", "Savings", 100, goal_id=goal_id)
    db.add_transaction(conn, date(2026, 8, 15), "Expense", "Savings", 100, goal_id=goal_id)
    assert db.get_goal_progress(conn, goal_id) == 200


def test_goal_progress_ignores_unrelated_transactions(conn):
    goal_id = db.add_goal(conn, "Emergency Fund", 1000)
    db.add_transaction(conn, date.today(), "Expense", "Groceries", 50)  # no goal_id
    assert db.get_goal_progress(conn, goal_id) == 0


def test_goal_monthly_rate(conn):
    goal_id = db.add_goal(conn, "Vacation", 2000)
    today = date(2026, 9, 16)
    db.add_transaction(conn, date(2026, 8, 1), "Expense", "Savings", 100, goal_id=goal_id)
    db.add_transaction(conn, date(2026, 9, 1), "Expense", "Savings", 200, goal_id=goal_id)
    # months=2 window starting Aug 1; total 300 / 2 = 150
    rate = db.get_goal_monthly_rate(conn, goal_id, months=2)
    assert rate == pytest.approx(150.0)


def test_archive_goal(conn):
    goal_id = db.add_goal(conn, "Old Goal", 500)
    db.archive_goal(conn, goal_id)
    assert db.get_goals(conn).empty
    assert not db.get_goals(conn, include_archived=True).empty


# --------------------------------------------------------------------------- #
# Backup / restore
# --------------------------------------------------------------------------- #


def test_export_import_round_trip(conn):
    db.add_transaction(conn, date(2026, 1, 1), "Income", "Salary", 5000)
    db.set_budget(conn, "Groceries", 300)
    data = db.export_data(conn)

    fresh = db.get_connection(":memory:")
    db.import_data(fresh, data, replace=True)

    df = db.get_transactions(fresh)
    assert len(df) == 1
    assert df.iloc[0]["amount"] == 5000

    budgets = db.get_budgets(fresh)
    assert budgets.loc[budgets["category"] == "Groceries", "monthly_limit"].iloc[0] == 300


def test_import_replace_clears_old_data(conn):
    db.add_transaction(conn, date.today(), "Expense", "Groceries", 10)
    db.import_data(conn, {}, replace=True)
    assert db.get_transactions(conn).empty
    assert db.get_categories(conn, include_archived=True).empty
