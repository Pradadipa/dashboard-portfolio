"""Service layer untuk customer operations."""
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.customer import (
    CustomerSummary,
    CustomerRFM,
    RFMSegment,
    TopCustomersResponse,
    TopCustomer,
    AcquisitionTrenPoint,
    AcquisitionTrend,
    CohortRetentionCell,
    CohortRetentionResponse,
    CohortRetentionRow,
    ChannelMetrics,
    AcquisitionChannelQualityResponse,
)
from app.core.utils import mask_email

# The demo dataset ends in July 2026, so reports are anchored there instead of "today".
REPORT_END_MONTH = date(2026, 7, 1)


def _month_window(end_month: date, months: int) -> tuple[date, date]:
    """(first month, first day after the last month) of the `months` months ending at end_month."""
    start_month = end_month - relativedelta(months=months - 1)
    end_month_next = end_month + relativedelta(months=1)
    return start_month, end_month_next


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

async def get_top_customers(
        db: AsyncSession,
        limit: int = 10
) -> TopCustomersResponse:
    """
    Get top N customers by lifetime value with RFM segment classification.
    
    Query: 
    - Compute RFM scoring untuk semua customer (CTE)
    - Classify segment
    - Join dengan customer master data
    - Order by amount_spent DESC, limit N
    """
    query = text("""
        WITH customer_metrics AS (
            SELECT
                customer_id,
                number_of_orders AS frequency,
                amount_spent AS monetary,
                (DATE '2026-07-31' - last_order_at::date) AS recency_days
            FROM shopify.customers
            WHERE number_of_orders > 0
                AND last_order_at IS NOT NULL
        ),
        scored AS (
            SELECT
                customer_id,
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
                customer_id,
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
            c.customer_id,
            c.display_name,
            c.email,
            c.amount_spent AS lifetime_value,
            c.number_of_orders AS orders_count,
            c.first_purchase_at::date AS first_purchase_at,
            c.last_order_at::date AS last_order_at,
            (CURRENT_DATE - c.last_order_at::date) AS days_since_last_order,
            c.country,
            c.province,
            COALESCE(s.segment, 'Others') AS rfm_segment
        FROM shopify.customers c
        LEFT JOIN segmented s ON s.customer_id = c.customer_id
        WHERE c.number_of_orders > 0
            AND c.amount_spent IS NOT NULL
            AND c.amount_spent > 0
        ORDER BY c.amount_spent DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {"limit": limit})
    rows = result.all()

    # Transform to response schema with masking
    customers = []
    for idx, row in enumerate(rows):
        customers.append(TopCustomer(
            rank=idx+1,
            customer_id=row.customer_id,
            display_name=row.display_name,
            email_masked=mask_email(row.email),
            lifetime_value=Decimal(str(row.lifetime_value)),
            orders_count=int(row.orders_count),
            first_purchase_at=row.first_purchase_at,
            last_order_at=row.last_order_at,
            days_since_last_order=int(row.days_since_last_order),
            country=row.country,
            province=row.province,
            rfm_segment=row.rfm_segment
        ))

    # Get total count for reference
    count_query = text("SELECT COUNT(*) AS cnt FROM shopify.customers WHERE number_of_orders > 0")
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return TopCustomersResponse(
        total_customers=int(total),
        limit=limit,
        customers=customers
    )

async def get_acquisition_trend(
        db: AsyncSession,
        months: int = 12,
        *,
        end_month: date = REPORT_END_MONTH,
) -> AcquisitionTrend:
    """
    Get customer acquisition trend selama N bulan terakhir.
    
    Returns time series dengan 2 metrics per bulan:
    - new_customers: first_purchase_at di bulan tsb
    - returning_customers: ada order di bulan tsb tapi first_purchase sebelumnya
    
    Plus context metrics untuk header KPI:
    - current_month_total: active di bulan terakhir
    - mom_change_percent: growth vs bulan sebelumnya
    - current_repeat_rate: repeat rate di bulan terakhir
    """

    # Calculate period range
    start_month, end_month_next = _month_window(end_month, months)

    query = text("""
        WITH months AS (
            SELECT generate_series(
                CAST(:start_month AS date),
                CAST(:end_month AS date),
                '1 month'::interval
            )::date AS month_start
        ),
        new_per_month AS (
            SELECT
                date_trunc('month', first_purchase_at AT TIME ZONE 'America/New_York')::date AS month_start,
                COUNT(DISTINCT customer_id) AS new_count
            FROM
                shopify.customers
            WHERE first_purchase_at IS NOT NULL
                AND (first_purchase_at AT TIME ZONE 'America/New_York')::date >= :start_month
                AND (first_purchase_at AT TIME ZONE 'America/New_York')::date < :end_month_next
            GROUP BY
                month_start
        ),
        returning_per_month AS (
            SELECT
                date_trunc('month', (o.created_at AT TIME ZONE 'America/New_York')::date)::date AS month_start,
                COUNT(DISTINCT o.customer_id) AS returning_count
            FROM shopify.orders o
            JOIN shopify.customers c ON c.customer_id = o.customer_id
            WHERE c.first_purchase_at IS NOT NULL
                AND date_trunc('month', c.first_purchase_at AT TIME ZONE 'America/New_York') < date_trunc('month', (o.created_at AT TIME ZONE 'America/New_York')::date)
                AND (o.created_at AT TIME ZONE 'America/New_York')::date >= :start_month
                AND (o.created_at AT TIME ZONE 'America/New_York')::date < :end_month_next
            GROUP BY month_start
        )
        SELECT
            m.month_start,
            COALESCE(n.new_count, 0) AS new_count,
            COALESCE(r.returning_count, 0) AS returning_count
        FROM months m
        LEFT JOIN new_per_month n ON n.month_start = m.month_start
        LEFT JOIN returning_per_month r ON r.month_start = m.month_start
        ORDER BY m.month_start ASC
    """)

    result = await db.execute(
        query, 
        {
            "start_month": start_month, 
            "end_month":end_month, 
            "end_month_next":end_month_next}
    )
    rows = result.all()

    # Build data points dengan repeat rate per point
    data_points = []
    total_new = 0
    total_returning = 0

    for row in rows:
        new_count = int(row.new_count)
        returning_count = int(row.returning_count)
        total = new_count + returning_count

        # Repeat rate per bulan
        repeat_rate = (
            (Decimal(returning_count) / Decimal(total) * 100).quantize(Decimal("0.01"))
            if total > 0
            else Decimal("0.00")
        )

        data_points.append(AcquisitionTrenPoint(
            month=row.month_start.strftime("%Y-%m"),
            new_customers=new_count,
            returning_customers=returning_count,
            total_active=total,
            repeat_rate_percent=repeat_rate
        ))

        total_new += new_count
        total_returning += returning_count

    current_total = data_points[-1].total_active if data_points else 0
    prev_total = data_points[-2].total_active if len(data_points) >= 2 else 0
    current_repeat_rate = (
        data_points[-1].repeat_rate_percent if data_points else Decimal("0.00")
    )

    # MoM change
    mom_change = None
    if prev_total > 0:
        mom_change = (
            (Decimal(current_total - prev_total) / Decimal(prev_total) * 100)
            .quantize(Decimal("0.01"))
        )

    return AcquisitionTrend(
        start_month=start_month.strftime("%Y-%m"),
        end_month=end_month.strftime("%Y-%m"),
        data_points=data_points,
        total_new=total_new,
        total_returning=total_returning,
        current_month_total=current_total,
        mom_change_percent=mom_change,
        current_repeat_rate=current_repeat_rate,
    )

async def get_cohort_retention(
        db: AsyncSession,
        cohort_count: int = 12,
        period_count: int = 6,
        *,
        end_month: date = REPORT_END_MONTH,
) -> CohortRetentionResponse:
    """
    Hitung cohort retention matrix.
    
    Setiap cohort = bulan customer first_purchase_at.
    Retention % = (returners di period N) / cohort_size * 100.
    
    Period incomplete (belum lewat full month) di-return sebagai None.
    """
    query = text("""
        WITH cohort_customers AS (
            SELECT
                customer_id,
                date_trunc('month', first_purchase_at AT TIME ZONE 'America/New_York')::date AS cohort_month
            FROM shopify.customers
            WHERE first_purchase_at IS NOT NULL
                AND (first_purchase_at AT TIME ZONE 'America/New_York')::date >= :start_month
                AND (first_purchase_at AT TIME ZONE 'America/New_York')::date < :end_month_next
        ),
        cohort_sizes AS (
            SELECT
                cohort_month,
                COUNT(DISTINCT customer_id) AS cohort_size
            FROM cohort_customers
            GROUP BY cohort_month
        ),
        customer_orders_monthly AS (
            SELECT DISTINCT
                o.customer_id,
                date_trunc('month', o.created_at AT TIME ZONE 'America/New_York')::date AS order_month
            FROM shopify.orders o
            JOIN cohort_customers cc ON cc.customer_id = o.customer_id
        ),
        cohort_retention AS (
            SELECT
                cc.cohort_month,
                (EXTRACT(YEAR FROM AGE(com.order_month, cc.cohort_month)) * 12 +
                EXTRACT(MONTH FROM AGE(com.order_month, cc.cohort_month)))::int AS period_number,
                COUNT(DISTINCT cc.customer_id) AS returners
            FROM cohort_customers cc
            JOIN customer_orders_monthly com ON com.customer_id = cc.customer_id
            WHERE com.order_month > cc.cohort_month
            GROUP BY cc.cohort_month, period_number
        )
        SELECT
            cs.cohort_month,
            cs.cohort_size,
            cr.period_number,
            COALESCE(cr.returners, 0) AS returners
        FROM cohort_sizes cs
        -- Period filter lives in ON, not WHERE, so cohorts without returners still show up
        LEFT JOIN cohort_retention cr ON cr.cohort_month = cs.cohort_month
            AND cr.period_number BETWEEN 1 AND :period_count
        ORDER BY cs.cohort_month ASC, cr.period_number ASC
    """)

    start_month, end_month_next = _month_window(end_month, cohort_count)

    result = await db.execute(
        query,
        {
            "period_count": period_count,
            "start_month": start_month,
            "end_month_next": end_month_next,
        }
    )
    raw_rows = result.mappings().all()

    cohort_map: dict[date, dict] = {}
    for row in raw_rows:
        cohort_month = row["cohort_month"]
        if cohort_month not in cohort_map:
            cohort_map[cohort_month] = {
                "cohort_size": row["cohort_size"],
                "cells_by_period":{}
            }
        # A cohort without returners comes back as one row with period_number NULL
        if row["period_number"] is not None:
            cohort_map[cohort_month]["cells_by_period"][row["period_number"]] = row["returners"]

    # Build final response
    rows_output = []
    for cohort_month in sorted(cohort_map.keys()):
        data = cohort_map[cohort_month]
        cohort_size = data["cohort_size"]
        cells_by_period = data["cells_by_period"]

        cells = []
        for period in range(1, period_count + 1):
            # Periode N artinya cohort_month + N bulan; belum lengkap kalau lewat end_month
            is_incomplete = cohort_month + relativedelta(months=period) > end_month

            returners = cells_by_period.get(period, 0)

            if is_incomplete:
                retention_pct = None
            else:
                retention_pct = round(100.0 * returners / cohort_size, 2) if cohort_size > 0 else 0.0

            cells.append(CohortRetentionCell(
                period_number=period,
                returners=returners,
                retention_pct=retention_pct
            ))

        rows_output.append(CohortRetentionRow(
            cohort_month=cohort_month,
            cohort_size=cohort_size,
            cells=cells
        ))

    return CohortRetentionResponse(
        cohort_count=len(rows_output),
        period_count=period_count,
        rows=rows_output
    )


async def get_acquisition_channel_quality(
    db: AsyncSession,
    *,
    reference_date: date = REPORT_END_MONTH,
) -> AcquisitionChannelQualityResponse:
    """
    Hitung channel quality untuk cohort 180-90 hari sebelum reference_date.

    Metrics per channel:
    - new_customers: volume
    - pct_of_total: share dari total
    - repeat_by_m3_pct: % customer yang return dalam 90 hari dari first purchase
    - avg_projected_12mo_value: amount_spent × (12 / tenure_months)
    - hibernating_pct: % customer dengan last_order > 180 hari lalu (R_score <= 2)

    Channel normalization logic MIRRORS ga4.v_monthly_channel_conversion di schema
    supaya widget konsisten dengan dashboard GA4 lain.
    """
    cohort_start = reference_date - relativedelta(days=180)
    cohort_end = reference_date - relativedelta(days=90)
    hibernating_threshold = reference_date - relativedelta(days=180)

    query = text("""
        WITH cohort_customers AS (
            SELECT
                c.customer_id,
                c.first_purchase_at,
                c.first_order_id,
                c.amount_spent,
                c.last_order_at,
                c.number_of_orders,
                -- Tenure dalam bulan dari reference_date. GREATEST(..., 3) sebagai
                -- defensive floor; cohort window selalu 3-6 bulan jadi normalnya tidak kena.
                GREATEST(
                    EXTRACT(YEAR FROM AGE(
                        CAST(:reference_date AS date),
                        (c.first_purchase_at AT TIME ZONE 'America/New_York')::date
                    )) * 12 +
                    EXTRACT(MONTH FROM AGE(
                        CAST(:reference_date AS date),
                        (c.first_purchase_at AT TIME ZONE 'America/New_York')::date
                    )),
                    3
                )::int AS tenure_months
            FROM shopify.customers c
            WHERE c.first_purchase_at IS NOT NULL
              AND (c.first_purchase_at AT TIME ZONE 'America/New_York')::date >= :cohort_start
              AND (c.first_purchase_at AT TIME ZONE 'America/New_York')::date < :cohort_end
              AND c.number_of_orders > 0
        ),
        first_order_channels AS (
            -- Join ke attribution via first_order_id untuk dapat channel acquisition.
            -- Logic normalization mirror ga4.v_monthly_channel_conversion (schema.sql).
            SELECT
                cc.customer_id,
                cc.first_purchase_at,
                cc.amount_spent,
                cc.last_order_at,
                cc.tenure_months,
                CASE
                    WHEN a.traffic_channel = 'Paid Social'                        THEN 'Paid Social'
                    WHEN a.traffic_channel IN ('Paid Search','Paid Other','Paid') THEN 'Paid Search'
                    WHEN a.traffic_channel = 'Email'                              THEN 'Email'
                    WHEN a.traffic_channel IN ('SMS','Text')                      THEN 'SMS'
                    WHEN a.traffic_channel = 'Seo'
                         OR LOWER(a.traffic_source) IN ('google','bing','yahoo','duckduckgo') THEN 'Organic Search'
                    WHEN LOWER(a.traffic_source) = 'direct'                       THEN 'Direct'
                    WHEN LOWER(a.traffic_source) IN ('facebook','instagram')      THEN 'Organic Social'
                    WHEN a.order_id IS NULL                                       THEN 'Unknown'
                    ELSE 'Unassigned'
                END AS channel
            FROM cohort_customers cc
            LEFT JOIN shopify.order_attribution a ON a.order_id = cc.first_order_id
        ),
        m3_returners AS (
            -- Customer yang punya order kedua dalam 90 hari dari first_purchase.
            -- > bukan >= untuk exclude the first order itself.
            SELECT DISTINCT fc.customer_id
            FROM first_order_channels fc
            JOIN shopify.orders o ON o.customer_id = fc.customer_id
            WHERE o.created_at > fc.first_purchase_at
              AND o.created_at <= fc.first_purchase_at + INTERVAL '90 days'
        ),
        channel_aggregated AS (
            SELECT
                fc.channel,
                COUNT(*)                                                     AS new_customers,
                COUNT(*) FILTER (WHERE m3.customer_id IS NOT NULL)           AS repeated_m3,
                AVG(fc.amount_spent * 12.0 / fc.tenure_months)               AS avg_projected_12mo,
                COUNT(*) FILTER (
                    WHERE (fc.last_order_at AT TIME ZONE 'America/New_York')::date
                          < :hibernating_threshold
                )                                                            AS hibernating_count
            FROM first_order_channels fc
            LEFT JOIN m3_returners m3 ON m3.customer_id = fc.customer_id
            GROUP BY fc.channel
        )
        SELECT
            channel,
            new_customers,
            repeated_m3,
            ROUND(100.0 * new_customers / NULLIF(SUM(new_customers) OVER (), 0), 1) AS pct_of_total,
            ROUND(100.0 * repeated_m3 / NULLIF(new_customers, 0), 1)                AS repeat_by_m3_pct,
            ROUND(COALESCE(avg_projected_12mo, 0), 0)                               AS avg_projected_12mo_value,
            ROUND(100.0 * hibernating_count / NULLIF(new_customers, 0), 1)          AS hibernating_pct
        FROM channel_aggregated
        WHERE new_customers > 0
        ORDER BY new_customers DESC
    """)

    result = await db.execute(
        query,
        {
            "cohort_start": cohort_start,
            "cohort_end": cohort_end,
            "reference_date": reference_date,
            "hibernating_threshold": hibernating_threshold,
        },
    )
    rows = result.mappings().all()

    channels = [
        ChannelMetrics(
            channel=row["channel"],
            new_customers=int(row["new_customers"]),
            pct_of_total=row["pct_of_total"] or Decimal("0"),
            repeat_by_m3_pct=row["repeat_by_m3_pct"] or Decimal("0"),
            avg_projected_12mo_value=row["avg_projected_12mo_value"] or Decimal("0"),
            hibernating_pct=row["hibernating_pct"] or Decimal("0"),
        )
        for row in rows
    ]

    # Weighted average M3 repeat rate (benchmark line di chart).
    # Pakai total_m3_returners / total_new supaya cohort kecil tidak distorsi.
    total_new = sum(int(row["new_customers"]) for row in rows)
    total_m3_returners = sum(int(row["repeated_m3"]) for row in rows)
    avg_repeat_by_m3 = (
        (Decimal(total_m3_returners) * 100 / Decimal(total_new))
        if total_new > 0 else Decimal("0")
    )

    top = channels[0] if channels else None

    return AcquisitionChannelQualityResponse(
        cohort_start=cohort_start,
        cohort_end=cohort_end,
        total_new_customers=total_new,
        avg_repeat_by_m3_pct=round(avg_repeat_by_m3, 1),
        top_channel=top.channel if top else "N/A",
        top_channel_share=top.pct_of_total if top else Decimal("0"),
        top_channel_repeat_rate=top.repeat_by_m3_pct if top else Decimal("0"),
        channels=channels,
    )


