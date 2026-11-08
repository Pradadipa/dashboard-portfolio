"""
Tests for get_customer_rfm_segmentation() - customer counts per RFM segment.

The date range decides WHO is counted (customers with an order in the range, by New York
date). It must not change a customer's label: labels are scored against every customer,
so they agree with the Top Customers table whatever range is selected.
"""

from datetime import date, datetime
from decimal import Decimal

from app.services.customer_service import get_customer_rfm_segmentation, get_customer_summary
from tests.factories import add_customer, add_order, set_session_tz, utc

JULY = (date(2026, 7, 1), date(2026, 7, 31))


async def add_buyer(
    db,
    customer_id: int,
    *order_times: datetime,
    number_of_orders: int = 1,
    amount_spent: str = "100.00",
) -> None:
    await add_customer(
        db,
        customer_id,
        order_times[0],
        number_of_orders=number_of_orders,
        last_order_at=order_times[-1],
        amount_spent=amount_spent,
    )
    for index, order_time in enumerate(order_times):
        await add_order(db, customer_id * 100 + index, order_time, customer_id=customer_id)


async def test_counts_only_customers_with_an_order_in_range(db):
    await add_buyer(db, 1, utc(2026, 7, 10))
    await add_buyer(db, 2, utc(2026, 7, 20))
    await add_buyer(db, 3, utc(2026, 6, 20))  # same segment, outside the range

    rfm = await get_customer_rfm_segmentation(db, *JULY)

    assert rfm.total_active_customers == 2
    assert [(s.segment, s.customer_count, s.percentage) for s in rfm.segments] == [
        ("New Customers", 2, Decimal("100.00")),
    ]


async def test_range_uses_new_york_dates(db):
    await add_buyer(db, 1, utc(2026, 7, 1, 2, 0))  # Jun 30 22:00 NY -> out
    await add_buyer(db, 2, utc(2026, 7, 1, 4, 0))  # Jul 1 00:00 NY -> in
    await add_buyer(db, 3, utc(2026, 8, 1, 3, 30))  # Jul 31 23:30 NY -> in
    await add_buyer(db, 4, utc(2026, 8, 1, 4, 0))  # Aug 1 00:00 NY -> out
    await set_session_tz(db)

    rfm = await get_customer_rfm_segmentation(db, *JULY)

    assert rfm.total_active_customers == 2


async def test_customer_with_many_orders_in_range_counts_once(db):
    await add_buyer(db, 1, utc(2026, 7, 10), utc(2026, 7, 20), number_of_orders=2)

    rfm = await get_customer_rfm_segmentation(db, *JULY)

    assert rfm.total_active_customers == 1


async def test_label_is_scored_against_all_customers_not_just_the_range(db):
    # Customers 1-4 spend less, so customer 5 sits in the top spend group (m_score 5) and
    # is a Champion. Scored only against the July buyers, customer 5 would be alone and
    # land in the lowest spend group (m_score 1), which is "Others".
    for customer_id, spent in [(1, "100.00"), (2, "200.00"), (3, "300.00"), (4, "400.00")]:
        await add_buyer(db, customer_id, utc(2026, 6, 15), number_of_orders=4, amount_spent=spent)
    await add_buyer(db, 5, utc(2026, 7, 15), number_of_orders=4, amount_spent="500.00")

    rfm = await get_customer_rfm_segmentation(db, *JULY)

    assert [(s.segment, s.customer_count) for s in rfm.segments] == [("Champions", 1)]


async def test_range_without_orders_returns_no_segments(db):
    await add_buyer(db, 1, utc(2026, 6, 20))

    rfm = await get_customer_rfm_segmentation(db, *JULY)

    assert rfm.total_active_customers == 0
    assert rfm.segments == []


async def test_total_matches_customer_summary_total(db):
    await add_buyer(db, 1, utc(2026, 7, 10))
    await add_buyer(db, 2, utc(2026, 7, 10), utc(2026, 7, 20), number_of_orders=2)
    await add_buyer(db, 3, utc(2026, 6, 20))

    rfm = await get_customer_rfm_segmentation(db, *JULY)
    summary = await get_customer_summary(db, *JULY)

    assert rfm.total_active_customers == summary.total_customers == 2


async def test_endpoint_applies_the_date_range(db, client):
    await add_buyer(db, 1, utc(2026, 7, 10))
    await add_buyer(db, 2, utc(2026, 6, 20))

    response = await client.get(
        "/api/customers/rfm", params={"start_date": "2026-07-01", "end_date": "2026-07-31"}
    )

    assert response.status_code == 200
    assert response.json()["total_active_customers"] == 1


async def test_endpoint_rejects_end_date_before_start_date(client):
    response = await client.get(
        "/api/customers/rfm", params={"start_date": "2026-07-31", "end_date": "2026-07-01"}
    )

    assert response.status_code == 400
