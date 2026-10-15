"""Service layer untuk customer operations."""
from datetime import date
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.customer import CustomerSummary, CustomerRFM, RFMSegment

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

async def get_customer_rfm_segmentation(
        db: AsyncSession
) -> CustomerRFM:
    """
    Compute RFM segmentation untuk semua active customers.
    
    Hybrid scoring approach:
    - R (Recency): Fixed buckets (0-90, 90-180, 180-365, 1-2yr, 2yr+)
    - F (Frequency): Fixed buckets (1, 2, 3, 4-10, 11+)
    - M (Monetary): NTILE(5) auto-balance
    
    Returns 10 segment classifications dengan metrics per segment.
    """

    query=text("""
        WITH customer_metrics AS (
            SELECT
                customer_id,
                display_name,
                number_of_orders AS frequency,
                amount_spent AS monetary,
                (DATE '2026-07-31' - last_order_at::date) AS recency_days
            FROM shopify.customers
            WHERE number_of_orders > 0
                AND last_order_at IS NOT NULL
        ),
        scored AS (
            SELECT
                *,
                CASE
                    WHEN recency_days <= 90 THEN 5
                    WHEN recency_days <= 180 THEN 4
                    WHEN recency_days <= 365 THEN 3
                    WHEN recency_days <= 730 THEN 2
                    ELSE 1
                END AS r_score,
                CASE
                    WHEN frequency >= 11 THEN 5
                    WHEN frequency BETWEEN 4 AND 10 THEN 4
                    WHEN frequency = 3 THEN 3
                    WHEN frequency = 2 THEN 2
                    ELSE 1
                END AS f_score,
                NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
            FROM customer_metrics
        ),
        segmented AS (
            SELECT
                *,
                CASE
                    WHEN r_score = 5 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
                    WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 3 THEN 'Loyal'
                    WHEN r_score <= 2 AND f_score = 5 THEN 'Cant Lose Them'
                    WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 3 THEN 'At Risk'
                    WHEN r_score = 5 AND f_score = 1 THEN 'New Customers'
                    WHEN r_score >= 4 AND f_score BETWEEN 2 AND 3 AND m_score >= 3 THEN 'Potential Loyalists'
                    WHEN r_score >= 4 AND f_score = 1 AND m_score >= 3 THEN 'Promising'
                    WHEN r_score = 3 THEN 'About to Sleep'
                    WHEN r_score = 2 THEN 'Hibernating'
                    WHEN r_score = 1 THEN 'Lost'
                    ELSE 'Others'
                END AS segment
            FROM scored
        )
        SELECT
            segment,
            COUNT(*) AS customer_count,
            ROUND(AVG(monetary)::numeric, 2) AS avg_lifetime_value,
            ROUND(SUM(monetary)::numeric, 2) AS total_lifetime_value,
            ROUND(AVG(frequency)::numeric, 1) AS avg_orders,
            ROUND(AVG(recency_days)::numeric, 0) AS avg_days_since_order,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
        FROM segmented
        GROUP BY segment
        ORDER BY
            CASE segment
                WHEN 'Champions' THEN 1
                WHEN 'Loyal' THEN 2
                WHEN 'Cant Lose Them' THEN 3
                WHEN 'At Risk' THEN 4
                WHEN 'Potential Loyalists' THEN 5
                WHEN 'Promising' THEN 6
                WHEN 'New Customers' THEN 7
                WHEN 'About to Sleep' THEN 8
                WHEN 'Hibernating' THEN 9
                WHEN 'Lost' THEN 10
                ELSE 11
            END
    """)

    result = await db.execute(query)
    rows = result.all()

    # Build segment list
    segments = [
        RFMSegment(
            segment=row.segment,
            customer_count=int(row.customer_count),
            avg_lifetime_value=Decimal(str(row.avg_lifetime_value)),
            total_lifetime_value=Decimal(str(row.total_lifetime_value)),
            avg_orders=Decimal(str(row.avg_orders)),
            avg_days_since_order=int(row.avg_days_since_order),
            percentage=Decimal(str(row.percentage))
        ) for row in rows
    ]

    # Calculate total active customers (sum of all segment counts)
    total_active = sum(s.customer_count for s in segments)

    return CustomerRFM(
        reference_date=date.today(),
        total_active_customers=total_active,
        segments=segments
    )