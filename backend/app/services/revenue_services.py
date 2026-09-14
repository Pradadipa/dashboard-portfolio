from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
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
    SparklinePoint,
    MonthlyRevenue,
    YearlyRevenueComparison
    )

def calc_change_percent(current: Decimal, previous: Decimal) -> Decimal | None:
    """
    Hitung % change vs previous.
    Return None kalau previous = 0 (tidak bisa hitung growth).
    """
    if previous == 0:
        return None
    change = ((current - previous) / previous) * 100
    return change.quantize(Decimal("0.01"))

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
            COALESCE(SUM(CASE WHEN row_type = 'SALE' THEN amount ELSE 0 END), 0) AS total_sales,
            COALESCE(SUM(CASE WHEN row_type = 'RETURN' THEN amount ELSE 0 END), 0) AS total_returns_negative,
            COALESCE(SUM(amount), 0) AS net_sales,
            COALESCE(COUNT(DISTINCT CASE WHEN row_type = 'SALE' THEN order_id END), 0) AS total_orders
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
            return None
        change = ((current_val - previous_val)/previous_val) * 100
        return change.quantize(Decimal("0.01"))

    previous_net_sales = Decimal(previous.net_sales)
    previous_total_sales = Decimal(previous.total_sales)
    previous_total_returns = abs(Decimal(previous.total_returns_negative))
    previous_orders = previous.total_orders or 0
    previous_aov = (previous_net_sales/previous_orders) if previous_orders > 0 else Decimal("0.00")

    net_sales_change = calc_change(net_sales, previous_net_sales)
    total_sales_change = calc_change(total_sales, previous_total_sales)
    total_return_change = calc_change(total_returns, previous_total_returns)
    orders_change = calc_change(Decimal(total_orders), Decimal(previous_orders))
    aov_change = calc_change(aov, previous_aov)

    # 7. Build sparkline points
    net_sales_sparkline = [
        SparklinePoint(
            date=row.date,
            value=Decimal(row.net_sales).quantize(Decimal("0.01")),
        )
        for row in sparkline_rows
    ]
    
    total_sales_sparkline = [
        SparklinePoint(
            date=row.date,
            value=Decimal(row.total_sales).quantize(Decimal("0.01")),
        )
        for row in sparkline_rows
    ]
    
    total_returns_sparkline = [
        SparklinePoint(
            date=row.date,
            value=abs(Decimal(row.total_returns_negative)).quantize(Decimal("0.01")),
        )
        for row in sparkline_rows
    ]
    
    orders_sparkline = [
        SparklinePoint(
            date=row.date,
            value=Decimal(row.total_orders or 0),
        )
        for row in sparkline_rows
    ]

    aov_sparkline = [
        SparklinePoint(
            date=row.date,
            value=(
                Decimal(row.net_sales) / Decimal(row.total_orders)
                if row.total_orders and row.total_orders > 0
                else Decimal("0.00")
            ).quantize(Decimal("0.01")),
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
        # Percentage changes
        net_sales_change_percent=net_sales_change,
        total_sales_change_percent=total_sales_change,            # ← TAMBAH
        total_returns_change_percent=total_return_change,         # ← TAMBAH (perhatikan nama variable-mu singular)
        orders_change_percent=orders_change,
        aov_change_percent=aov_change,
        # Sparklines
        net_sales_sparkline=net_sales_sparkline,
        total_sales_sparkline=total_sales_sparkline,
        total_returns_sparkline=total_returns_sparkline,
        orders_sparkline=orders_sparkline,
        aov_sparkline=aov_sparkline,
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
    
    # Step 1: Hitung previous period
    previous_start = start_date - relativedelta(years=1)
    previous_end = end_date - relativedelta(years=1)

    # Step 2: Mapping granularity ke PostgreSQL date_trunc unit
    trunc_unit_map = {
        Granularity.DAY: "day",
        Granularity.WEEK: "week",
        Granularity.MONTH: "month"
    }
    trunc_unit = trunc_unit_map[granularity]

    # Step 3: Query template
    query = text(f"""
        SELECT
            date_trunc('{trunc_unit}', date_key)::date AS period_date,
            COALESCE(SUM(amount), 0) AS net_sales,
            COUNT(DISTINCT CASE WHEN row_type = 'SALE' THEN order_id END) AS orders
        FROM shopify.v_net_sales_lines
        WHERE date_key >= :start_date AND date_key <= :end_date
        GROUP BY period_date
        ORDER BY period_date ASC
    """)

    # Step 4: Query current period
    current_result = await db.execute(
        query,
        {"start_date": start_date, "end_date": end_date}
    )
    current_rows = current_result.all()

    # Step 5: Query previous period
    previous_result = await db.execute(
        query,
        {"start_date": previous_start, "end_date": previous_end}
    )
    previous_rows = previous_result.all()

    # Step 6: Build lookup
    previous_lookup: dict[tuple[int, int], dict] = {}
    for row in previous_rows:
        key = (row.period_date.month, row.period_date.day)
        previous_lookup[key] = {
            "net_sales": Decimal(row.net_sales),
            "orders": int(row.orders or 0)
        }

    # Step 7: Merge current and previous
    data_points = []
    current_total_net_sales = Decimal("0")
    previous_total_net_sales = Decimal("0")
    current_total_orders = 0
    previous_total_orders = 0
    for row in current_rows:
        current_date = row.period_date
        key = (current_date.month, current_date.day)

        current_net_sales = Decimal(row.net_sales)
        current_orders = int(row.orders or 0)

        previous_data = previous_lookup.get(key, {
            "net_sales": Decimal("0"),
            "orders": 0,
        })
        previous_net_sales = previous_data["net_sales"]
        previous_orders = previous_data["orders"]

        # Calc change per point
        net_sales_change = calc_change_percent(current_net_sales, previous_net_sales)
        orders_change = calc_change_percent(
            Decimal(current_orders),
            Decimal(previous_orders),
        )
        
        data_points.append(RevenueTrendPoint(
            date=current_date,
            current_net_sales=current_net_sales.quantize(Decimal("0.01")),
            current_orders=current_orders,
            previous_net_sales=previous_net_sales.quantize(Decimal("0.01")),
            previous_orders=previous_orders,
            net_sales_change_percent=net_sales_change,
            orders_change_percent=orders_change,
        ))

        # Accumulate totals
        current_total_net_sales += current_net_sales
        previous_total_net_sales += previous_net_sales
        current_total_orders += current_orders
        previous_total_orders += previous_orders

    # Step 7: Calc overall change
    overall_net_sales_change = calc_change_percent(
        current_total_net_sales,
        previous_total_net_sales,
    )
    overall_orders_change = calc_change_percent(
        Decimal(current_total_orders),
        Decimal(previous_total_orders),
    )
    
    return RevenueTrend(
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        data_points=data_points,
        total_points=len(data_points),
        current_total_net_sales=current_total_net_sales.quantize(Decimal("0.01")),
        previous_total_net_sales=previous_total_net_sales.quantize(Decimal("0.01")),
        current_total_orders=current_total_orders,
        previous_total_orders=previous_total_orders,
        net_sales_change_percent=overall_net_sales_change,
        orders_change_percent=overall_orders_change,
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
        WITH channel_totals AS (
            SELECT
                traffic_channel AS channel,
                SUM(orders) AS orders,
                SUM(net_revenue) AS revenue
            FROM shopify.v_daily_sales_by_channel
            WHERE order_date >= :start_date
                AND order_date <= :end_date
            GROUP BY traffic_channel
        ),
        ranked AS (
            SELECT
                channel,
                orders,
                revenue,
                ROW_NUMBER() OVER (ORDER BY revenue DESC NULLS LAST) AS rn
            FROM channel_totals
        )
        SELECT
            CASE WHEN rn <= 4 THEN channel ELSE 'Other' END AS channel,
            SUM(orders) AS orders,
            SUM(revenue) AS revenue
        FROM ranked
        GROUP BY CASE WHEN rn <= 4 THEN channel ELSE 'Other' END
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

async def get_yearly_revenue_comparison(
        db: AsyncSession
) -> YearlyRevenueComparison:
    """
    Ambil revenue per bulan untuk tahun ini dan tahun lalu.
    
    Berguna untuk widget YoY comparison chart.
    Data yang di-return: 12 bulan × 2 tahun.
    """
    current_year = date(2026,1,1).year
    previous_year = current_year -1

    # Query: aggregate revenue per (year, month)
    # Cover 2 years: current + previous
    query = text("""
        SELECT
            EXTRACT(YEAR FROM date_key)::int AS year,
            EXTRACT(MONTH FROM date_key)::int AS month,
            COALESCE(SUM(amount), 0) AS revenue
        FROM shopify.v_net_sales_lines
        WHERE date_key >= make_date(:previous_year,1,1)
            AND date_key < make_date(:next_year,1,1)
        GROUP BY year, month
        ORDER BY year, month
    """)

    result = await db.execute(
        query,
        {
            "previous_year": previous_year,
            "next_year": current_year + 1
        }
    )

    rows = result.all()

    # Build lookup dict
    revenue_lookup: dict[tuple[int, int], Decimal] = {}
    for row in rows:
        revenue_lookup[(row.year, row.month)] = Decimal(row.revenue)

    # Month labels
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Build response
    monthly_data = []
    current_year_total = Decimal("0")
    previous_year_total = Decimal("0")

    for month_num in range(1,13):
        current_rev = revenue_lookup.get((current_year, month_num), Decimal("0"))
        previous_rev = revenue_lookup.get((previous_year, month_num), Decimal("0"))

        monthly_data.append(MonthlyRevenue(
            month=month_labels[month_num - 1],
            month_number=month_num,
            current_year_revenue=current_rev.quantize(Decimal("0.01")),
            previous_year_revenue=previous_rev.quantize(Decimal("0.01"))
        ))

        current_year_total += current_rev
        previous_year_total += previous_rev

        # YoY change
    yoy_change = None
    if previous_year_total > 0:
        yoy_change = (
            (current_year_total - previous_year_total) / previous_year_total * 100
        ).quantize(Decimal("0.01"))

    return YearlyRevenueComparison(
        current_year=current_year,
        previous_year=previous_year,
        data=monthly_data,
        current_year_total=current_year_total.quantize(Decimal("0.01")),
        previous_year_total=previous_year_total.quantize(Decimal("0.01")),
        yoy_change_percent=yoy_change,
    )