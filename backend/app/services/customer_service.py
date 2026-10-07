"""Service layer untuk customer operations."""
from datetime import date
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.customer import CustomerSummary

async def get_customer_summary(
        db: AsyncSession,
        start_date: date,
        end_date: date
) -> CustomerSummary:

    # Query 1: Total active customers + new + returning
    counts_query = text("""
        WITH active_customers AS (
            SELECT DISTINCT c.customer_id, c.customer_since
            FROM shopify.customers c
            JOIN shopify.orders o ON o.customer_id = c.customer_id
            WHERE (o.created_at AT TIME ZONE 'America/New_York')::date >= :start_date
                AND (o.created_at AT TIME ZONE 'America/New_York')::date <= :end_date
        )
        SELECT
            COUNT(*) AS total_customers,
            COUNT(*) FILTER (
                WHERE (customer_since AT TIME ZONE 'America/New_York')::date >= :start_date
                    AND (customer_since AT TIME ZONE 'America/New_York')::date <= :end_date
            ) AS new_customers,
            COUNT(*) FILTER (
                WHERE (customer_since AT TIME ZONE 'America/New_York')::date < :start_date
            ) AS returning_customers
        FROM
            active_customers
    """)

    counts_result = await db.execute(
        counts_query,{"start_date": start_date, "end_date": end_date}
    )
    counts = counts_result.one()

    # Query 2: Average LTV + repeat purchase rate from active customers
    ltv_query = text("""
        WITH active_customers AS (
            SELECT DISTINCT c.customer_id, c.amount_spent, c.number_of_orders
            FROM shopify.customers c
            JOIN shopify.orders o ON o.customer_id = c.customer_id
            WHERE (o.created_at AT TIME ZONE 'America/New_York')::date >= :start_date
                AND (o.created_at AT TIME ZONE 'America/New_York')::date <= :end_date
        )
        SELECT
            COALESCE(AVG(amount_spent), 0) AS avg_ltv,
            COUNT(*) FILTER (WHERE number_of_orders > 1) AS repeat_customers,
            COUNT(*) AS total_active
        FROM active_customers
    """)

    ltv_result = await db.execute(
        ltv_query, {"start_date": start_date, "end_date": end_date}
    )
    ltv_row = ltv_result.one()

    # Calculate repeat purchase rate
    total_active = ltv_row.total_active or 0
    repeat_customers = ltv_row.repeat_customers or 0
    repeat_rate = (
        (Decimal(repeat_customers)/Decimal(total_active) * 100).quantize(Decimal("0.01"))
        if total_active > 0
        else Decimal("0.00")
    )

    return CustomerSummary(
        start_date=start_date,
        end_date=end_date,
        total_customers=counts.total_customers or 0,
        new_customers=counts.new_customers or 0,
        returning_customers=counts.returning_customers or 0,
        average_ltv=Decimal(ltv_row.avg_ltv).quantize(Decimal("0.01")),
        repeat_purchase_rate=repeat_rate,
        currency="USD"
    )