"""Static configuration and constants for Budget Planner.

Nothing in this file talks to Streamlit or SQLite — it's just data, so
every other module (and the test suite) can import it safely.
"""

from pathlib import Path

# The database always lives next to this file, regardless of the
# directory the app happens to be launched from.
DB_PATH = str(Path(__file__).parent / "budget.db")

# Default categories seeded into a brand-new database: (name, kind, icon)
# kind is "Income" or "Expense".
DEFAULT_CATEGORIES = [
    ("Salary", "Income", "💼"),
    ("Freelance", "Income", "🧾"),
    ("Interest/Dividends", "Income", "📈"),
    ("Other Income", "Income", "💵"),
    ("Rent/Mortgage", "Expense", "🏠"),
    ("Groceries", "Expense", "🛒"),
    ("Utilities", "Expense", "💡"),
    ("Transportation", "Expense", "🚗"),
    ("Dining Out", "Expense", "🍽️"),
    ("Entertainment", "Expense", "🎬"),
    ("Subscriptions", "Expense", "📱"),
    ("Health", "Expense", "🏥"),
    ("Shopping", "Expense", "🛍️"),
    ("Savings", "Expense", "🏦"),
    ("Other", "Expense", "🔖"),
]

FREQUENCIES = ["Weekly", "Monthly", "Yearly"]

CURRENCY_OPTIONS = {
    "USD ($)": "$",
    "EUR (€)": "€",
    "GBP (£)": "£",
    "JPY (¥)": "¥",
    "INR (₹)": "₹",
}

DEFAULT_CURRENCY_SYMBOL = "$"
