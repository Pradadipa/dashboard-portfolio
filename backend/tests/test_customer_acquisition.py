"""
Tests for get_acquisition_trend() - new vs returning customers per month.

A customer's first purchase belongs to the month it happened in New York time, whatever
time zone the database session runs in (dev runs in Asia/Kuala_Lumpur, the VPS may run
in UTC). These numbers must agree with the cohort sizes in get_cohort_retention().
"""

from datetime import date

from app.services.customer_service import get_acquisition_trend
from tests.factories import add_customer, add_order, set_session_tz, utc


async def test_new_customer_bucketed_by_new_york_month(db):
    await add_customer(db, 1, utc(2026, 7, 1, 2, 0))  # Jun 30 22:00 NY -> June
    await add_customer(db, 2, utc(2026, 7, 1, 4, 0))  # Jul 1 00:00 NY -> July
    await add_customer(db, 3, utc(2026, 7, 1, 14, 0))  # Jul 1 10:00 NY -> July
    await set_session_tz(db)

    trend = await get_acquisition_trend(db, months=2, end_month=date(2026, 7, 1))

    assert {p.month: p.new_customers for p in trend.data_points} == {
        "2026-06": 1,
        "2026-07": 2,
    }


async def test_new_customer_in_est_month(db):
    await add_customer(db, 1, utc(2026, 1, 1, 4, 30))  # Dec 31 23:30 EST -> December
    await set_session_tz(db, "UTC")

    trend = await get_acquisition_trend(db, months=2, end_month=date(2026, 1, 1))

    assert {p.month: p.new_customers for p in trend.data_points} == {
        "2025-12": 1,
        "2026-01": 0,
    }


async def test_window_is_n_months_ending_at_end_month(db):
    await set_session_tz(db)

    trend = await get_acquisition_trend(db, months=3, end_month=date(2026, 7, 1))

    assert [p.month for p in trend.data_points] == ["2026-05", "2026-06", "2026-07"]
    assert (trend.start_month, trend.end_month) == ("2026-05", "2026-07")

    one = await get_acquisition_trend(db, months=1, end_month=date(2026, 7, 1))

    assert [p.month for p in one.data_points] == ["2026-07"]


async def test_returning_uses_new_york_first_purchase_month(db):
    await add_customer(db, 1, utc(2026, 7, 1, 2, 0))  # first purchase in June (NY)
    await add_order(db, 101, utc(2026, 7, 1, 2, 0), customer_id=1)
    await add_order(db, 102, utc(2026, 7, 20), customer_id=1)  # returning in July
    await add_customer(db, 2, utc(2026, 7, 1, 14, 0))  # first purchase in July (NY)
    await add_order(db, 201, utc(2026, 7, 1, 14, 0), customer_id=2)
    await add_order(db, 202, utc(2026, 7, 20), customer_id=2)  # still new in July
    await set_session_tz(db)

    trend = await get_acquisition_trend(db, months=1, end_month=date(2026, 7, 1))

    assert trend.data_points[0].returning_customers == 1
    assert trend.data_points[0].new_customers == 1


async def test_zero_number_of_orders_still_counts_as_new(db):
    """Same definition as the cohort: having a first purchase is what makes a customer new."""
    await add_customer(db, 1, utc(2026, 7, 10), number_of_orders=0)

    trend = await get_acquisition_trend(db, months=1, end_month=date(2026, 7, 1))

    assert trend.data_points[0].new_customers == 1
