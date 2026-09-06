from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.revenue import (
    RevenueSummary, 
    RevenueTrendPoint, 
    RevenueTrend, 
    Granularity,
    RevenueByChannel,
    ChannelRevenue,
    SparklinePoint
    )

async def get_revenue_summary(
        db: AsyncSession,
        start_date: date,
        end_date: date,
) -> RevenueSummary:
    """
    Get revenue summary for a given date range.
    
    Args:
        db (AsyncSession): SQLAlchemy async session.
        start_date (date): Start date of the period.
        end_date (date): End date of the period.
    
    Returns:
        RevenueSummary: Summary of revenue metrics.
    """
    # 1. Query current period metrics
    current_query = text("""
        SELECT
            COALESCE(SUM(CASE WHEN row_type = 'SALE' THEN amount ELSE 0 END), 0) AS total_sales,
            COALESCE(SUM(CASE WHEN row_type = 'RETURN' THEN amount ELSE 0 END), 0) AS total_returns_negative,
            COALESCE(SUM(amount), 0) AS net_sales,
            COALESCE(COUNT(DISTINCT CASE WHEN row_type = 'SALE' THEN order_id END), 0) AS total_orders
        FROM 
            shopify.v_net_sales_lines
        WHERE 
            date_key >= :start_date AND date_key <= :end_date
    """)

    current_result = await db.execute(
        current_query, 
        {'start_date': start_date, 'end_date': end_date}
    )
    current = current_result.one()

    # 2. Calculate previous period range
    period_length = (end_date - start_date).days + 1
    previous_end_date = start_date - timedelta(days=1)
    previous_start_date = previous_end_date - timedelta(days=period_length-1)

    # 3. Query previous period range
    previous_result = await db.execute(
        current_query,
        {"start_date": previous_start_date, "end_date": previous_end_date}
    )
    previous = previous_result.one()

    # 4. Query sparkline data
    sparkline_query = text("""
        SELECT
            date_key AS date,
            COALESCE(SUM(amount), 0) AS value
        FROM shopify.v_net_sales_lines
        WHERE date_key >= :start_date AND date_key <= :end_date
        GROUP BY date_key
        ORDER BY date_key ASC
    """)
    sparkline_result = await db.execute(
        sparkline_query,
        {"start_date": start_date, "end_date": end_date}
    )
    sparkline_rows = sparkline_result.all()

    # 5. Calculate values
    # Convert DB to Decimal
    total_sales = Decimal(current.total_sales)
    total_returns = abs(Decimal(current.total_returns_negative))  # Ensure refunds are positive
    net_sales = Decimal(current.net_sales)
    total_orders = current.total_orders or 0  # Default to 0 if None

    # Calculate average order value, handling division by zero
    aov = (net_sales / total_orders) if total_orders > 0 else Decimal('0.00')

    # 6. Calculate percentage changes
    def calc_change(current_val: Decimal, previous_val: Decimal) -> Decimal | None:
        """Return % change, or none if previous = 0"""
        if previous_val == 0:
            return 0
        change = ((current_val - previous_val)/previous_val) * 100
        return change.quantize(Decimal("0.01"))

    previous_net_sales = Decimal(previous.net_sales)
    previous_orders = previous.total_orders or 0
    previous_aov = (previous_net_sales/previous_orders) if previous_orders > 0 else Decimal("0.00")

    net_sales_change = calc_change(net_sales, previous_net_sales)
    orders_change = calc_change(Decimal(total_orders), Decimal(previous_orders))
    aov_change = calc_change(aov, previous_aov)

    # 7. Build sparkline points
    sparkline_points = [
        SparklinePoint(
            date=row.date,
            value=Decimal(row.value).quantize(Decimal("0.01"))
        )
        for row in sparkline_rows
    ]
    # Return the revenue summary as a Pydantic model
    return RevenueSummary(
        start_date=start_date,
        end_date=end_date,
        total_sales=total_sales.quantize(Decimal('0.01')),  # Round to 2 decimal places
        total_returns=total_returns.quantize(Decimal('0.01')),  # Round to 2 decimal places
        net_sales=net_sales.quantize(Decimal('0.01')),  # Round to 2 decimal places
        total_orders=total_orders,
        average_order_value=aov.quantize(Decimal('0.01')),  # Round to 2 decimal places
        currency='USD',  # Assuming USD; adjust as necessary
        net_sales_change_percent=net_sales_change,
        orders_change_percent=orders_change,
        aov_change_percent=aov_change,
        net_sales_sparkline=sparkline_points
    )

async def get_revenue_trend(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        granularity: Granularity,
) -> RevenueTrend:
    """
    Ambil time series revenue untuk chart.
    
    Data di-aggregate per hari/minggu/bulan sesuai granularity.
    Data disusun dari tanggal terlama ke terbaru (untuk chart).
    
    Args:
        db: Async database session
        start_date: Tanggal mulai (inclusive)
        end_date: Tanggal akhir (inclusive)
        granularity: Level agregasi (day/week/month)
    
    Returns:
        RevenueTrend dengan array data_points
    """
    # Map granularity ke PostgreSQL date_trunc unit
    # date_trunc('day', '2026-07-15 10:30') → '2026-07-15 00:00'
    # date_trunc('week', '2026-07-15') → tanggal Senin di minggu itu
    # date_trunc('month', '2026-07-15') → '2026-07-01'
    trunc_unit = granularity.value  # 'day', 'week', atau 'month'

    query = text(f"""
        SELECT 
            date_trunc('{trunc_unit}', date_key)::date AS period_start,
            COALESCE(SUM(amount), 0) AS net_sales,
            COUNT(DISTINCT CASE WHEN row_type = 'SALE' THEN order_id END) AS orders
        FROM
            shopify.v_net_sales_lines
        WHERE
            date_key >= :start_date AND
            date_key <= :end_date
        GROUP BY period_start
        ORDER BY period_start ASC
    """)

    result = await db.execute(query, {"start_date": start_date, "end_date": end_date})
    rows = result.all() # ambil semua row (bukan .one() lagi karena banyak row)

    # Convert setiap ro ke revenueTrenPoint
    data_points = [
        RevenueTrendPoint(
            date=row.period_start,
            net_sales=Decimal(row.net_sales).quantize(Decimal("0.01")),
            orders=row.orders or 0
        )
        for row in rows
    ]

    return RevenueTrend(
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        data_points=data_points,
        total_points=len(data_points),
    )

async def get_revenue_by_channel(
        db: AsyncSession,
        start_date: date,
        end_date: date,
        limit: int | None = None,
) -> RevenueByChannel:
    """
    Ambil breakdown revenue per traffic channel.
    
    Menggunakan view v_daily_sales_by_channel yang sudah aggregate
    per (date, channel, source, device). Kita agg lebih lanjut per channel.
    
    Args:
        db: Async database session
        start_date: Tanggal mulai (inclusive)
        end_date: Tanggal akhir (inclusive)
        limit: Batasi jumlah channel (None = semua)
    
    Returns:
        RevenueByChannel dengan array channels sorted by revenue desc
    """
    query=text("""
        SELECT
            traffic_channel AS channel,
            SUM(orders) AS orders,
            SUM(net_revenue) AS revenue
        FROM shopify.v_daily_sales_by_channel
        WHERE order_date >= :start_date
            AND order_date <= :end_date
        GROUP BY traffic_channel
        ORDER BY revenue DESC NULLS LAST
    """)

    result = await db.execute(
        query,
        {"start_date":start_date, "end_date": end_date}
    )
    rows = result.all()

    if limit is not None:
        rows_display = rows[:limit]
    else:
        rows_display = rows

    total_revenue = sum(
        (Decimal(row.revenue) if row.revenue else Decimal("0")) for row in rows
    )

    total_orders = sum(row.orders for row in rows)

    channels = []
    for row in rows_display:
        row_revenue = Decimal(row.revenue) if row.revenue else Decimal("0") 

        if total_revenue > 0:
            percentage = (row_revenue/total_revenue *100).quantize(Decimal("0.01"))
        else:
            percentage = Decimal("0.00")

        channels.append(ChannelRevenue(
            channel=row.channel or "UNKNOWN",
            orders=row.orders or 0,
            revenue=row_revenue.quantize(Decimal("0.01")),
            percentage=percentage
        ))

    return RevenueByChannel(
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        total_revenue=total_revenue.quantize(Decimal("0.01")),
        total_order=total_orders
    )