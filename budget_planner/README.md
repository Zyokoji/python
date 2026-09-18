# Budget Planner

A personal budget tracker built with Python, SQLite, and Streamlit — multi-page,
tested, and designed to run entirely on your own machine with no external
accounts, no cloud sync, and no telemetry.

## Features

- **Transactions** — income and expenses with date, category, amount, and notes
- **Custom categories** — add your own, each with an icon; archive ones you no
  longer use without breaking old transactions that reference them
- **History** — filter by date range, type, category, or free-text search;
  edit or delete any transaction; export the filtered view to CSV
- **Budgets** — set a monthly limit per category; see live pacing ("on track"
  or "on pace to go $X over by month end"), not just a static total
- **Recurring transactions** — rent, subscriptions, paychecks, etc. Generated
  automatically whenever you open the app, correctly handling month-end
  rollovers (e.g. a Jan 31 monthly bill lands on Feb 28) and leap years
- **Savings goals** — a target amount and optional date, contributions
  tracked separately, with a plain-English completion projection based on
  your recent contribution rate
- **Backup & restore** — export everything to a JSON file and restore it
  later (or on a new machine)
- **Multi-currency display** — pick a symbol (USD/EUR/GBP/JPY/INR or custom)

## Project structure

```
budget_planner/
├── app.py                          # Home / overview page (entry point)
├── database.py                     # SQLite schema + all CRUD, no Streamlit dependency
├── utils.py                        # Currency formatting, date math, pacing/projection math
├── db_session.py                   # Cached shared DB connection + once-per-session recurring sync
├── config.py                       # Constants: default categories, currencies, frequencies
├── pages/
│   ├── 1_➕_Add_Transaction.py
│   ├── 2_📜_History.py
│   ├── 3_🎯_Budgets.py
│   ├── 4_🔁_Recurring.py
│   ├── 5_🏆_Goals.py
│   └── 6_⚙️_Settings.py
├── tests/
│   ├── test_database.py            # Unit tests for the data layer
│   ├── test_utils.py               # Unit tests for date/currency/pacing math
│   └── test_app_pages.py           # End-to-end tests: real Streamlit AppTest simulations
├── .streamlit/config.toml          # Theme
├── requirements.txt
├── requirements-dev.txt
└── budget.db                       # Created automatically on first run (not included)
```

**Why it's split this way:** `database.py` and `utils.py` contain zero
Streamlit imports, so all the actual logic — date math, budget math, CRUD —
is unit-testable in plain Python, fast, and independent of the UI. The
`pages/*.py` files are thin: they call into those modules and render
widgets. `db_session.py` bridges the two, using `st.cache_resource` so the
whole app shares one SQLite connection instead of reopening the file on
every click.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Your browser opens automatically to `http://localhost:8501`. All data is
stored in `budget.db`, a SQLite file created next to `app.py` on first run —
nothing leaves your machine.

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

54 tests, covering:
- Every CRUD operation and validation rule in the data layer
- Recurring-transaction date math, including month-end and leap-year edge
  cases (a Jan 31 monthly bill, a Feb 29 yearly one)
- Full user flows on every page — filling in forms and clicking buttons via
  Streamlit's official `AppTest` framework, then checking the database
  actually changed the way it should

## Known limitations

- Designed for a single user on one local machine at a time. Opening two
  browser tabs at the exact moment recurring transactions are first due
  could, in a rare race, generate one duplicate — safe to just delete it.
- The currency setting only changes the displayed symbol; it doesn't
  convert amounts between currencies.
- No authentication — anyone with access to your machine (or the `.db`
  file) can see your data.

## Ideas for extending it further

- Import bank statement CSVs (map columns to date/amount/category)
- Multiple accounts (checking, savings, credit card) with transfers between them
- Charts: category breakdown as a pie chart, net worth over time
- A "envelope"/zero-based budgeting mode
- Package it as a desktop app (e.g. with `pywebview`) instead of running
  `streamlit run` manually
