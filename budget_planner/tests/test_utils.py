from datetime import date

import utils


def test_format_currency():
    assert utils.format_currency(1234.5) == "$1,234.50"
    assert utils.format_currency(-42) == "-$42.00"
    assert utils.format_currency(0, "€") == "€0.00"


def test_month_bounds_regular_year():
    start, end = utils.month_bounds(date(2026, 2, 10))
    assert start == date(2026, 2, 1)
    assert end == date(2026, 2, 28)  # 2026 is not a leap year


def test_month_bounds_leap_year():
    start, end = utils.month_bounds(date(2024, 2, 10))
    assert end == date(2024, 2, 29)


def test_months_ago():
    assert utils.months_ago(date(2026, 9, 16), 0) == date(2026, 9, 1)
    assert utils.months_ago(date(2026, 9, 16), 2) == date(2026, 7, 1)
    assert utils.months_ago(date(2026, 1, 16), 1) == date(2025, 12, 1)


def test_budget_pace_on_track():
    result = utils.budget_pace(spent=100, limit_amount=400, today=date(2026, 9, 10))
    assert result["days_elapsed"] == 10
    assert result["on_track"] is True


def test_budget_pace_over_budget_projection():
    # $50/day for the first 5 days of a 30-day month projects to $1500
    result = utils.budget_pace(spent=250, limit_amount=400, today=date(2026, 9, 5))
    assert round(result["projected_total"]) == 1500
    assert result["on_track"] is False


def test_budget_pace_zero_limit():
    result = utils.budget_pace(spent=0, limit_amount=0, today=date(2026, 9, 5))
    assert result["on_track"] is True  # 0 spent, 0 projected, 0 <= 0


def test_project_goal_completion_reached():
    assert utils.project_goal_completion(1000, 1000, 100) == "Goal reached! 🎉"
    assert utils.project_goal_completion(1200, 1000, 100) == "Goal reached! 🎉"


def test_project_goal_completion_no_rate():
    assert "Add a contribution" in utils.project_goal_completion(0, 1000, 0)


def test_project_goal_completion_math():
    # Need $500 more, saving $100/month -> 5 months from Jan 1 2026 -> June 2026
    msg = utils.project_goal_completion(500, 1000, 100, today=date(2026, 1, 1))
    assert "5 months" in msg
    assert "June 2026" in msg


def test_project_goal_completion_year_rollover():
    # From November, 3 months needed should roll into the next year
    msg = utils.project_goal_completion(0, 300, 100, today=date(2026, 11, 15))
    assert "February 2027" in msg
