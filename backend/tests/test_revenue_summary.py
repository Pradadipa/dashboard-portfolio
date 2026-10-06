"""
Tests for app.services.revenue_services.get_revenue_summary (service layer, no HTTP).

Expected numbers are worked out by hand in tests/factories.py (seed_january_2026).
Query window: Jan 1-31 2026. Because the window is 31 days long, the "previous period"
is Dec 1-31 2025, which holds exactly one 100.00 order.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services.revenue_services import calc_change_percent, get_revenue_summary
from tests.factories import add_line, add_order, utc

JAN_1 = date(2026, 1, 1)
JAN_31 = date(2026, 1, 31)


async def test_summary_headline_numbers(db, january_2026):
    s = await get_revenue_summary(db, JAN_1, JAN_31)

    assert s.total_sales == Decimal("240.00")
    assert s.total_returns == Decimal("50.00")  # shown as a positive number
    assert s.net_sales == Decimal("190.00")
    assert s.total_orders == 3
    assert s.total_qty == 6  # 7 sold - 1 returned
    assert s.average_order_value == Decimal("63.33")  # 190 / 3
    assert s.currency == "USD"


async def test_summary_percent_change_vs_previous_period(db, january_2026):
    """Previous period (Dec): sales 100, returns 0, orders 1, qty 1, AOV 100."""
    s = await get_revenue_summary(db, JAN_1, JAN_31)

    assert s.net_sales_change_percent == Decimal("90.00")  # 190 vs 100
    assert s.total_sales_change_percent == Decimal("140.00")  # 240 vs 100
    assert s.orders_change_percent == Decimal("200.00")  # 3 vs 1
    assert s.total_qty_change_percent == Decimal("500.00")  # 6 vs 1
    assert s.aov_change_percent == Decimal("-36.67")  # 63.33 vs 100
    assert s.total_returns_change_percent is None  # previous returns were 0: no growth rate


async def test_summary_net_sales_sparkline_has_one_point_per_active_day(db, january_2026):
    s = await get_revenue_summary(db, JAN_1, JAN_31)

    points = [(p.date, p.value) for p in s.net_sales_sparkline]
    assert points == [
        (date(2026, 1, 10), Decimal("180.00")),  # orders 1001 + 1002 (NY date!)
        (date(2026, 1, 15), Decimal("60.00")),
        (date(2026, 1, 20), Decimal("-50.00")),  # the refund day
    ]


async def test_summary_orders_sparkline_counts_only_sales(db, january_2026):
    s = await get_revenue_summary(db, JAN_1, JAN_31)

    assert [p.value for p in s.orders_sparkline] == [2, 1, 0]  # a refund day has no new orders
    assert [p.value for p in s.aov_sparkline] == [
        Decimal("90.00"),
        Decimal("60.00"),
        Decimal("0.00"),  # no orders -> 0, not a division by zero
    ]


async def test_summary_single_day_respects_new_york_timezone(db, january_2026):
    """If days were cut in UTC, order 1002 would move to Jan 11 and this would be 130 / 1."""
    s = await get_revenue_summary(db, date(2026, 1, 10), date(2026, 1, 10))

    assert s.net_sales == Decimal("180.00")
    assert s.total_orders == 2


async def test_summary_refund_in_february_does_not_reduce_january(db, january_2026):
    january = await get_revenue_summary(db, JAN_1, JAN_31)
    february = await get_revenue_summary(db, date(2026, 2, 1), date(2026, 2, 28))

    assert january.total_returns == Decimal("50.00")  # the Feb refund is not in here
    assert february.total_returns == Decimal("20.00")
    assert february.net_sales == Decimal("30.00")  # 50.00 sale (order 1004) - 20.00 refund


async def test_summary_on_empty_database_is_all_zeros(db):
    """No data must not crash (division by zero) and must not invent growth rates."""
    s = await get_revenue_summary(db, JAN_1, JAN_31)

    assert s.net_sales == Decimal("0.00")
    assert s.total_orders == 0
    assert s.average_order_value == Decimal("0.00")
    assert s.net_sales_change_percent is None
    assert s.net_sales_sparkline == []


async def test_summary_money_is_exact_decimal_not_float(db):
    """0.10 + 0.20 is 0.30000000000000004 in float. The dashboard must stay exact."""
    await add_order(db, 1, utc(2026, 1, 5))
    await add_line(db, 1, 1, "SKU-A", 1, "0.10")
    await add_line(db, 2, 1, "SKU-B", 1, "0.20")

    s = await get_revenue_summary(db, JAN_1, JAN_31)

    assert s.net_sales == Decimal("0.30")


@pytest.mark.parametrize(
    ("current", "previous", "expected"),
    [
        ("150", "100", Decimal("50.00")),
        ("50", "100", Decimal("-50.00")),
        ("100", "100", Decimal("0.00")),
        ("10", "0", None),  # cannot grow from zero
        ("0", "0", None),
        ("1", "3", Decimal("-66.67")),  # rounded to 2 decimals
    ],
)
def test_calc_change_percent(current, previous, expected):
    assert calc_change_percent(Decimal(current), Decimal(previous)) == expected
