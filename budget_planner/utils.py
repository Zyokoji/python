"""Pure helper functions: currency formatting, date/month math, and
budget-pacing / goal-projection calculations.

No Streamlit or database imports here on purpose, so all of this is
trivially unit-testable (see tests/test_utils.py).
"""

from __future__ import annotations

import calendar
import math
from datetime import date
from typing import Optional


def format_currency(amount: float, symbol: str = "$") -> str:
    """Format a number as currency, e.g. -42 -> '-$42.00'."""
    sign = "-" if amount < 0 else ""
    return f"{sign}{symbol}{abs(amount):,.2f}"


def month_bounds(d: date) -> tuple[date, date]:
    """Return (first day, last day) of the month containing d."""
    start = d.replace(day=1)
    last_day = calendar.monthrange(d.year, d.month)[1]
    end = d.replace(day=last_day)
    return start, end


def months_ago(d: date, months: int) -> date:
    """First day of the month that is `months` months before d's month.

    months_ago(Sep 16 2026, 0) -> Sep 1 2026
    months_ago(Sep 16 2026, 2) -> Jul 1 2026
    """
    total = d.year * 12 + (d.month - 1) - months
    year, month0 = divmod(total, 12)
    return date(year, month0 + 1, 1)


def budget_pace(spent: float, limit_amount: float, today: date) -> dict:
    """Project a category's month-end total from its spend-to-date.

    Returns a dict with days_elapsed, days_remaining, projected_total,
    daily_allowance (how much/day is left to stay under budget), and
    on_track (bool).
    """
    start, end = month_bounds(today)
    days_total = (end - start).days + 1
    days_elapsed = min((today - start).days + 1, days_total)
    days_remaining = max(days_total - days_elapsed, 0)

    daily_avg = spent / days_elapsed if days_elapsed else 0.0
    projected_total = daily_avg * days_total
    remaining_budget = max(limit_amount - spent, 0.0)
    daily_allowance = remaining_budget / days_remaining if days_remaining else remaining_budget

    return {
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "projected_total": projected_total,
        "daily_allowance": daily_allowance,
        "on_track": projected_total <= limit_amount,
    }


def project_goal_completion(
    current: float, target: float, monthly_rate: float, today: Optional[date] = None
) -> str:
    """Human-readable projection of when a savings goal will be reached."""
    today = today or date.today()
    if current >= target:
        return "Goal reached! 🎉"
    if monthly_rate <= 0:
        return "Add a contribution to see a projection"
    months_needed = math.ceil((target - current) / monthly_rate)
    total = today.year * 12 + (today.month - 1) + months_needed
    year, month0 = divmod(total, 12)
    month_name = calendar.month_name[month0 + 1]
    plural = "s" if months_needed != 1 else ""
    return f"~{months_needed} month{plural} to go (around {month_name} {year})"
