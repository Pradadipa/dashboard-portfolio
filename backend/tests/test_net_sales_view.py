"""
Tests for shopify.v_net_sales_lines - THE definition of net sales.

Every revenue number in the dashboard is SUM(amount) over this view, so these rules
are the most valuable thing to protect. The data comes from `january_2026`
(see tests/factories.py for the full, hand-checkable scenario).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import text

from tests.factories import add_line, add_order, add_refund_line, utc


async def _rows(db, where: str = "TRUE", params: dict | None = None):
    result = await db.execute(
        text(
            f"""
            SELECT row_type, date_key, order_id, line_item_id, sku, quantity, amount
            FROM shopify.v_net_sales_lines
            WHERE {where}
            ORDER BY date_key, row_type DESC, line_item_id
            """
        ),
        params or {},
    )
    return result.all()


async def test_sale_books_on_local_new_york_date_not_utc(db, january_2026):
    """Order 1002 is placed at 03:30 UTC on Jan 11 = 22:30 on Jan 10 in New York."""
    rows = await _rows(db, "order_id = 1002 AND row_type = 'SALE'")

    assert {r.date_key for r in rows} == {date(2026, 1, 10)}


async def test_package_protection_lines_are_excluded(db, january_2026):
    """x-redo and ROUTEINS* lines are not products, so they never count as sales."""
    rows = await _rows(db, "order_id = 1002")

    assert [r.sku for r in rows] == ["SKU-A"]


async def test_refund_of_an_excluded_line_is_ignored(db, january_2026):
    """Refund 2 reverses the x-redo line. Its sale never counted, so neither may the return."""
    rows = await _rows(db, "row_type = 'RETURN' AND line_item_id = 4")

    assert rows == []


async def test_refund_books_on_the_day_it_was_processed(db, january_2026):
    """A return lands on the refund's date, not on the original order's date."""
    rows = await _rows(db, "row_type = 'RETURN' AND order_id = 1001")

    assert len(rows) == 1
    assert rows[0].date_key == date(2026, 1, 20)  # order was Jan 10
    assert rows[0].amount == Decimal("-50.00")
    assert rows[0].quantity == -1


async def test_refund_of_a_january_order_lands_in_february(db, january_2026):
    january = await _rows(db, "date_key BETWEEN '2026-01-01' AND '2026-01-31' AND order_id = 1003")
    february = await _rows(db, "date_key BETWEEN '2026-02-01' AND '2026-02-28' AND order_id = 1003")

    assert [r.row_type for r in january] == ["SALE"]
    assert [r.row_type for r in february] == ["RETURN"]


async def test_net_sales_is_the_sum_of_sales_and_returns(db, january_2026):
    total = await db.scalar(
        text(
            "SELECT SUM(amount) FROM shopify.v_net_sales_lines "
            "WHERE date_key BETWEEN '2026-01-01' AND '2026-01-31'"
        )
    )

    # 100 + 30 + 50 + 60 sold, minus 50 returned
    assert total == Decimal("190.00")


async def test_returns_are_negative_and_sales_are_positive(db, january_2026):
    rows = await _rows(db)

    assert rows  # sanity: the scenario produced data
    for r in rows:
        if r.row_type == "SALE":
            assert r.amount > 0 and r.quantity > 0
        else:
            assert r.amount < 0 and r.quantity < 0


async def test_view_is_empty_on_an_empty_database(db):
    assert await _rows(db) == []


async def test_a_line_sold_in_pieces_can_be_refunded_in_pieces(db):
    """The schema allows one line to be refunded as two 1-unit events (see schema.sql)."""
    await add_order(db, 1, utc(2026, 3, 1))
    await add_line(db, 10, 1, "SKU-A", 2, "40.00")
    await add_refund_line(db, 100, 1, 10, utc(2026, 3, 5), 1, "40.00")
    await add_refund_line(db, 101, 1, 10, utc(2026, 3, 6), 1, "40.00")

    total = await db.scalar(text("SELECT SUM(amount) FROM shopify.v_net_sales_lines"))

    assert total == Decimal("0.00")  # 80.00 sold, 80.00 refunded
