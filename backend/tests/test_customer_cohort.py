"""
Tests for get_cohort_retention() - cohorts by first-purchase month.

Cohort sizes must equal get_acquisition_trend()'s new customers for the same months,
so both use the same New York month and the same window.
"""

from datetime import date

from app.services.customer_service import get_acquisition_trend, get_cohort_retention
from tests.factories import add_customer, add_order, set_session_tz, utc


async def test_cohort_window_matches_cohort_count(db):
    await add_customer(db, 1, utc(2026, 5, 1, 2, 0))  # Apr 30 22:00 NY -> outside
    await add_customer(db, 2, utc(2026, 5, 1, 14, 0))  # May
    await add_customer(db, 3, utc(2026, 7, 31, 20, 0))  # Jul 31 16:00 NY -> July
    await set_session_tz(db)

    resp = await get_cohort_retention(db, cohort_count=3, end_month=date(2026, 7, 1))

    assert {r.cohort_month: r.cohort_size for r in resp.rows} == {
        date(2026, 5, 1): 1,
        date(2026, 7, 1): 1,
    }

    one = await get_cohort_retention(db, cohort_count=1, end_month=date(2026, 7, 1))

    assert [r.cohort_month for r in one.rows] == [date(2026, 7, 1)]


async def test_cohort_without_returners_is_listed(db):
    await add_customer(db, 1, utc(2026, 6, 10))
    await add_order(db, 101, utc(2026, 6, 10), customer_id=1)

    resp = await get_cohort_retention(db, cohort_count=2, end_month=date(2026, 7, 1))

    assert [(r.cohort_month, r.cohort_size) for r in resp.rows] == [(date(2026, 6, 1), 1)]
    assert all(c.returners == 0 for c in resp.rows[0].cells)


async def test_new_customers_equal_cohort_sizes(db):
    """Headline regression: the two widgets agree month by month."""
    first_purchases = [
        utc(2026, 3, 1, 2),  # Feb 28 21:00 EST -> outside the Mar-Jul window
        utc(2026, 3, 1, 14),  # March
        utc(2026, 4, 30, 23),  # April
        utc(2026, 5, 1, 3, 59),  # Apr 30 23:59 EDT -> April
        utc(2026, 6, 15),  # June
        utc(2026, 7, 1, 4),  # Jul 1 00:00 EDT -> July
        utc(2026, 7, 31, 23),  # July
    ]
    for customer_id, first_purchase_at in enumerate(first_purchases, start=1):
        await add_customer(db, customer_id, first_purchase_at)
    await add_customer(db, 99, None)  # never purchased -> counted nowhere
    await set_session_tz(db)

    trend = await get_acquisition_trend(db, months=5, end_month=date(2026, 7, 1))
    cohort = await get_cohort_retention(db, cohort_count=5, end_month=date(2026, 7, 1))

    new = {p.month: p.new_customers for p in trend.data_points if p.new_customers}
    sizes = {r.cohort_month.strftime("%Y-%m"): r.cohort_size for r in cohort.rows}
    assert new == sizes
    assert sum(sizes.values()) == 6
