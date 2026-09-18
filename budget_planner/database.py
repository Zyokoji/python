"""database.py — Data layer for Budget Planner.

Pure Python + sqlite3, with no Streamlit dependency, so every function
here can be unit tested in isolation (see tests/test_database.py).
Callers pass `date` objects for dates; this module handles conversion
to/from SQLite's TEXT storage.
"""

from __future__ import annotations

import calendar
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd

import config
import utils

# --------------------------------------------------------------------------- #
# Connection & schema
# --------------------------------------------------------------------------- #


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open a SQLite connection, ensure schema + default data exist.

    `db_path` defaults to `config.DB_PATH`, resolved at call time (not
    baked in as a function-definition-time default) so tests can safely
    monkeypatch `config.DB_PATH` before calling this.
    """
    if db_path is None:
        db_path = config.DB_PATH
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    seed_defaults(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS categories (
            name     TEXT PRIMARY KEY,
            kind     TEXT NOT NULL CHECK(kind IN ('Income', 'Expense')),
            icon     TEXT NOT NULL DEFAULT '🏷️',
            archived INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS goals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            target_amount REAL NOT NULL CHECK(target_amount > 0),
            target_date   TEXT,
            archived      INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS recurring (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            type      TEXT NOT NULL CHECK(type IN ('Income', 'Expense')),
            category  TEXT NOT NULL REFERENCES categories(name),
            amount    REAL NOT NULL CHECK(amount > 0),
            frequency TEXT NOT NULL CHECK(frequency IN ('Weekly', 'Monthly', 'Yearly')),
            next_date TEXT NOT NULL,
            active    INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT NOT NULL,
            type         TEXT NOT NULL CHECK(type IN ('Income', 'Expense')),
            category     TEXT NOT NULL REFERENCES categories(name),
            amount       REAL NOT NULL CHECK(amount > 0),
            note         TEXT NOT NULL DEFAULT '',
            recurring_id INTEGER REFERENCES recurring(id) ON DELETE SET NULL,
            goal_id      INTEGER REFERENCES goals(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS budgets (
            category      TEXT PRIMARY KEY REFERENCES categories(name),
            monthly_limit REAL NOT NULL CHECK(monthly_limit >= 0)
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
        CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
        CREATE INDEX IF NOT EXISTS idx_transactions_goal ON transactions(goal_id);
        """
    )
    conn.commit()


def seed_defaults(conn: sqlite3.Connection) -> None:
    for name, kind, icon in config.DEFAULT_CATEGORIES:
        conn.execute(
            "INSERT OR IGNORE INTO categories (name, kind, icon) VALUES (?, ?, ?)",
            (name, kind, icon),
        )
    conn.execute(
        "INSERT OR IGNORE INTO app_settings (key, value) VALUES ('currency_symbol', ?)",
        (config.DEFAULT_CURRENCY_SYMBOL,),
    )
    conn.commit()


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


# --------------------------------------------------------------------------- #
# Categories
# --------------------------------------------------------------------------- #


def get_categories(conn, kind: Optional[str] = None, include_archived: bool = False) -> pd.DataFrame:
    query = "SELECT * FROM categories WHERE 1=1"
    params: list = []
    if kind:
        query += " AND kind = ?"
        params.append(kind)
    if not include_archived:
        query += " AND archived = 0"
    query += " ORDER BY name"
    return pd.read_sql_query(query, conn, params=params)


def add_category(conn, name: str, kind: str, icon: str = "🏷️") -> None:
    name = (name or "").strip()
    if not name:
        raise ValueError("Category name cannot be empty.")
    if kind not in ("Income", "Expense"):
        raise ValueError("Category kind must be 'Income' or 'Expense'.")
    conn.execute(
        "INSERT INTO categories (name, kind, icon, archived) VALUES (?, ?, ?, 0) "
        "ON CONFLICT(name) DO UPDATE SET kind = excluded.kind, icon = excluded.icon, archived = 0",
        (name, kind, icon or "🏷️"),
    )
    conn.commit()


def set_category_archived(conn, name: str, archived: bool) -> None:
    conn.execute("UPDATE categories SET archived = ? WHERE name = ?", (int(archived), name))
    conn.commit()


# --------------------------------------------------------------------------- #
# Transactions
# --------------------------------------------------------------------------- #


def add_transaction(
    conn,
    tx_date: date,
    tx_type: str,
    category: str,
    amount: float,
    note: str = "",
    recurring_id: Optional[int] = None,
    goal_id: Optional[int] = None,
) -> int:
    if tx_type not in ("Income", "Expense"):
        raise ValueError("Transaction type must be 'Income' or 'Expense'.")
    if amount is None or amount <= 0:
        raise ValueError("Amount must be greater than 0.")
    if not category:
        raise ValueError("Category is required.")
    cur = conn.execute(
        "INSERT INTO transactions (date, type, category, amount, note, recurring_id, goal_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (tx_date.isoformat(), tx_type, category, float(amount), note or "", recurring_id, goal_id),
    )
    conn.commit()
    return cur.lastrowid


def update_transaction(conn, tx_id: int, **fields) -> None:
    if not fields:
        return
    allowed = {"date", "type", "category", "amount", "note", "goal_id"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Cannot update fields: {sorted(unknown)}")
    if "amount" in fields and fields["amount"] <= 0:
        raise ValueError("Amount must be greater than 0.")
    if "type" in fields and fields["type"] not in ("Income", "Expense"):
        raise ValueError("Transaction type must be 'Income' or 'Expense'.")
    if "date" in fields and isinstance(fields["date"], date):
        fields["date"] = fields["date"].isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [tx_id]
    conn.execute(f"UPDATE transactions SET {set_clause} WHERE id = ?", params)
    conn.commit()


def delete_transaction(conn, tx_id: int) -> None:
    conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()


def get_transactions(
    conn,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    tx_type: Optional[str] = None,
    search: Optional[str] = None,
) -> pd.DataFrame:
    query = "SELECT * FROM transactions WHERE 1=1"
    params: list = []
    if start_date:
        query += " AND date >= ?"
        params.append(start_date.isoformat())
    if end_date:
        query += " AND date <= ?"
        params.append(end_date.isoformat())
    if category:
        query += " AND category = ?"
        params.append(category)
    if tx_type:
        query += " AND type = ?"
        params.append(tx_type)
    if search:
        like = f"%{search}%"
        query += " AND (note LIKE ? OR category LIKE ?)"
        params.extend([like, like])
    query += " ORDER BY date DESC, id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def get_transaction(conn, tx_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()


# --------------------------------------------------------------------------- #
# Budgets
# --------------------------------------------------------------------------- #


def set_budget(conn, category: str, monthly_limit: float) -> None:
    if monthly_limit < 0:
        raise ValueError("Budget limit cannot be negative.")
    conn.execute(
        "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?) "
        "ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit",
        (category, monthly_limit),
    )
    conn.commit()


def delete_budget(conn, category: str) -> None:
    conn.execute("DELETE FROM budgets WHERE category = ?", (category,))
    conn.commit()


def get_budgets(conn) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM budgets ORDER BY category", conn)


# --------------------------------------------------------------------------- #
# Recurring transactions
# --------------------------------------------------------------------------- #


def add_recurring(
    conn, name: str, tx_type: str, category: str, amount: float, frequency: str, start_date: date
) -> int:
    if frequency not in config.FREQUENCIES:
        raise ValueError(f"Frequency must be one of {config.FREQUENCIES}")
    if tx_type not in ("Income", "Expense"):
        raise ValueError("Type must be 'Income' or 'Expense'.")
    if amount <= 0:
        raise ValueError("Amount must be greater than 0.")
    cur = conn.execute(
        "INSERT INTO recurring (name, type, category, amount, frequency, next_date, active) "
        "VALUES (?, ?, ?, ?, ?, ?, 1)",
        (name, tx_type, category, float(amount), frequency, start_date.isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def get_recurring(conn, active_only: bool = False) -> pd.DataFrame:
    query = "SELECT * FROM recurring"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY next_date"
    df = pd.read_sql_query(query, conn)
    if not df.empty:
        df["next_date"] = pd.to_datetime(df["next_date"]).dt.date
    return df


def set_recurring_active(conn, recurring_id: int, active: bool) -> None:
    conn.execute("UPDATE recurring SET active = ? WHERE id = ?", (int(active), recurring_id))
    conn.commit()


def delete_recurring(conn, recurring_id: int) -> None:
    conn.execute("DELETE FROM recurring WHERE id = ?", (recurring_id,))
    conn.commit()


def _advance_date(d: date, frequency: str) -> date:
    """Step a date forward by one period, handling month-end/leap-year edges."""
    if frequency == "Weekly":
        return d + timedelta(weeks=1)
    if frequency == "Monthly":
        month = d.month + 1
        year = d.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    if frequency == "Yearly":
        try:
            return d.replace(year=d.year + 1)
        except ValueError:  # Feb 29 on a non-leap year
            return d.replace(year=d.year + 1, day=28)
    raise ValueError(f"Unknown frequency: {frequency}")


def process_recurring(conn, as_of: Optional[date] = None) -> int:
    """Generate any due recurring transactions up to `as_of` (default today).

    Safe to call as often as you like: items whose next_date is already
    in the future are left untouched, and each due occurrence is only
    ever generated once, since next_date is advanced and persisted
    immediately after each one.
    """
    as_of = as_of or date.today()
    generated = 0
    rows = conn.execute("SELECT * FROM recurring WHERE active = 1").fetchall()
    for row in rows:
        next_date = datetime.strptime(row["next_date"], "%Y-%m-%d").date()
        safety = 0  # guards against a corrupt next_date causing a runaway loop
        while next_date <= as_of and safety < 1000:
            add_transaction(
                conn,
                next_date,
                row["type"],
                row["category"],
                row["amount"],
                note=f"Recurring: {row['name']}",
                recurring_id=row["id"],
            )
            generated += 1
            next_date = _advance_date(next_date, row["frequency"])
            safety += 1
        conn.execute("UPDATE recurring SET next_date = ? WHERE id = ?", (next_date.isoformat(), row["id"]))
    conn.commit()
    return generated


# --------------------------------------------------------------------------- #
# Goals
# --------------------------------------------------------------------------- #


def add_goal(conn, name: str, target_amount: float, target_date: Optional[date] = None) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Goal name cannot be empty.")
    if target_amount <= 0:
        raise ValueError("Target amount must be greater than 0.")
    cur = conn.execute(
        "INSERT INTO goals (name, target_amount, target_date) VALUES (?, ?, ?)",
        (name, float(target_amount), target_date.isoformat() if target_date else None),
    )
    conn.commit()
    return cur.lastrowid


def get_goals(conn, include_archived: bool = False) -> pd.DataFrame:
    query = "SELECT * FROM goals"
    if not include_archived:
        query += " WHERE archived = 0"
    query += " ORDER BY id"
    df = pd.read_sql_query(query, conn)
    if not df.empty:
        df["target_date"] = pd.to_datetime(df["target_date"]).dt.date
    return df


def archive_goal(conn, goal_id: int) -> None:
    conn.execute("UPDATE goals SET archived = 1 WHERE id = ?", (goal_id,))
    conn.commit()


def get_goal_progress(conn, goal_id: int) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE goal_id = ?",
        (goal_id,),
    ).fetchone()
    return float(row["total"]) if row else 0.0


def get_goal_monthly_rate(conn, goal_id: int, months: int = 3) -> float:
    """Average monthly contribution to a goal over the last `months` months."""
    cutoff = utils.months_ago(date.today(), months - 1)
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE goal_id = ? AND date >= ?",
        (goal_id, cutoff.isoformat()),
    ).fetchone()
    total = float(row["total"]) if row else 0.0
    return total / months


# --------------------------------------------------------------------------- #
# Backup / restore
# --------------------------------------------------------------------------- #

# Parent tables before children, so INSERTs satisfy foreign keys.
_ALL_TABLES = ["categories", "goals", "recurring", "transactions", "budgets", "app_settings"]


def export_data(conn) -> dict:
    return {t: [dict(r) for r in conn.execute(f"SELECT * FROM {t}").fetchall()] for t in _ALL_TABLES}


def import_data(conn, data: dict, replace: bool = False) -> None:
    if replace:
        for t in reversed(_ALL_TABLES):  # children before parents
            conn.execute(f"DELETE FROM {t}")
    for t in _ALL_TABLES:
        for row in data.get(t, []):
            cols = ", ".join(row.keys())
            placeholders = ", ".join("?" for _ in row)
            conn.execute(
                f"INSERT OR REPLACE INTO {t} ({cols}) VALUES ({placeholders})",
                list(row.values()),
            )
    conn.commit()
