"""
Helpers that insert small, hand-checkable rows with plain SQL.

Why SQL and not ORM models: services read through the `shopify.*` tables/views,
which are defined in db/schema.sql and have no SQLAlchemy models.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def utc(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


async def add_order(
    db: AsyncSession,
    order_id: int,
    created_at: datetime,
    *,
    net_payment: str | None = None,
    channel: str | None = None,
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO shopify.orders
                (order_id, order_name, created_at, total_amount, net_payment, total_refunded)
            VALUES (:id, :name, :created_at, :amount, :amount, 0)
            """
        ),
        {
            "id": order_id,
            "name": f"#{order_id}",
            "created_at": created_at,
            "amount": Decimal(net_payment) if net_payment else None,
        },
    )
    if channel:
        await db.execute(
            text(
                "INSERT INTO shopify.order_attribution (order_id, traffic_channel) "
                "VALUES (:id, :channel)"
            ),
            {"id": order_id, "channel": channel},
        )
    await db.commit()


async def add_line(
    db: AsyncSession,
    line_item_id: int,
    order_id: int,
    sku: str,
    quantity: int,
    unit_price: str,
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO shopify.order_line_items
                (line_item_id, order_id, sku, title, quantity, current_quantity,
                 discounted_unit_price)
            VALUES (:line_item_id, :order_id, :sku, :sku, :quantity, :quantity, :price)
            """
        ),
        {
            "line_item_id": line_item_id,
            "order_id": order_id,
            "sku": sku,
            "quantity": quantity,
            "price": Decimal(unit_price),
        },
    )
    await db.commit()


async def add_refund_line(
    db: AsyncSession,
    refund_id: int,
    order_id: int,
    line_item_id: int,
    processed_at: datetime,
    quantity: int,
    subtotal: str,
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO shopify.refund_line_items
                (refund_id, order_id, line_item_id, processed_at, quantity, subtotal)
            VALUES (:refund_id, :order_id, :line_item_id, :processed_at, :quantity, :subtotal)
            """
        ),
        {
            "refund_id": refund_id,
            "order_id": order_id,
            "line_item_id": line_item_id,
            "processed_at": processed_at,
            "quantity": quantity,
            "subtotal": Decimal(subtotal),
        },
    )
    await db.commit()


async def seed_january_2026(db: AsyncSession) -> None:
    """
    A small shop, built so every expected number can be checked by hand.
    All dates below are New York dates (the business timezone, UTC-5 in winter).

    December 2025 (the "previous period" for a Jan 1-31 query)
      order 900   Dec 15  SKU-A  1 x 100.00                          = 100.00

    January 2026
      order 1001  Jan 10  SKU-A  2 x  50.00 = 100.00
                          SKU-B  1 x  30.00 =  30.00
      order 1002  Jan 10  SKU-A  1 x  50.00 =  50.00   <- placed 03:30 UTC on Jan 11,
                                                          still the evening of Jan 10 in NY
                          x-redo        1.98  (package protection: never counts)
                          ROUTEINS-123  2.50  (package protection: never counts)
      order 1003  Jan 15  SKU-C  3 x  20.00 =  60.00
      refund      Jan 20  order 1001, SKU-A, 1 unit  -50.00
      refund      Jan 20  order 1002, x-redo line     (ignored: its sale never counted)

    February 2026 (outside a January query)
      refund      Feb  2  order 1003, SKU-C, 1 unit  -20.00  (a January order, refunded in Feb)
      order 1004  Feb  3  SKU-A  1 x 50.00

    Expected for Jan 1-31:
      total_sales 240.00   total_returns 50.00   net_sales 190.00
      total_orders 3       total_qty 6 (7 sold - 1 returned)   AOV 190 / 3 = 63.33
    """
    # December 2025
    await add_order(db, 900, utc(2025, 12, 15, 17, 0))
    await add_line(db, 9001, 900, "SKU-A", 1, "100.00")

    # January 2026
    await add_order(db, 1001, utc(2026, 1, 10, 15, 0))
    await add_line(db, 1, 1001, "SKU-A", 2, "50.00")
    await add_line(db, 2, 1001, "SKU-B", 1, "30.00")

    await add_order(db, 1002, utc(2026, 1, 11, 3, 30))
    await add_line(db, 3, 1002, "SKU-A", 1, "50.00")
    await add_line(db, 4, 1002, "x-redo", 1, "1.98")
    await add_line(db, 5, 1002, "ROUTEINS-123", 1, "2.50")

    await add_order(db, 1003, utc(2026, 1, 15, 17, 0))
    await add_line(db, 6, 1003, "SKU-C", 3, "20.00")

    await add_refund_line(db, 1, 1001, 1, utc(2026, 1, 20, 15, 0), 1, "50.00")
    await add_refund_line(db, 2, 1002, 4, utc(2026, 1, 20, 15, 0), 1, "1.98")

    # February 2026
    await add_refund_line(db, 3, 1003, 6, utc(2026, 2, 2, 15, 0), 1, "20.00")
    await add_order(db, 1004, utc(2026, 2, 3, 15, 0))
    await add_line(db, 7, 1004, "SKU-A", 1, "50.00")
