from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.revenue import ( 
    RevenueSummary, 
    RevenueTrend, 
    Granularity, 
    RevenueByChannel,
    YearlyRevenueComparison
)
from app.services.revenue_services import (
    get_revenue_summary, 
    get_revenue_trend, 
    get_revenue_by_channel,
    get_yearly_revenue_comparison
)

router =  APIRouter(prefix="/api/revenue", tags=["revenue"])

@router.get(
    "/summary",
    response_model=RevenueSummary,
    summary="Get revenue summary for specific period",
)
async def revenue_summary(
    start_date: date = Query(
        default=date(2026,1,1),
        description="Start date period (default: 30 days ago)",
        examples=["2026-07-01"]
    ),
    end_date: date = Query(
            default=date(2026,1,31),
            description="End date period (default: today)",
            examples=["2026-07-31"]
    ),
    db: AsyncSession = Depends(get_db),
) -> RevenueSummary:
    """
    Get revenue summary untuk periode tertentu.
    
    Data diambil dari view `shopify.v_net_sales_lines` yang merupakan
    single source of truth untuk net sales calculation.
    
    - **start_date**: Tanggal mulai (inclusive), default 30 hari lalu
    - **end_date**: Tanggal akhir (inclusive), default hari ini
    
    Timezone: America/New_York (sesuai timezone bisnis Shopify).
    """

    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail=f"end_date ({end_date} cannot be before start_date ({start_date}))"
        )

    days_diff = (end_date - start_date).days
    if days_diff > 730:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum range 2 years (730 days). Your range: {days_diff} days"
        )

    return await get_revenue_summary(db, start_date, end_date)

@router.get(
    "/trend",
    response_model=RevenueTrend,
    summary="Get revenue time series for chart"
)
async def revenue_trend(
    start_date: date = Query(
        default=date(2026,1,1),
        description="Start date period (default: 30 days ago)",
        examples=["2026-01-01"]
    ),
    end_date: date = Query(
        default=date(2026,1,31),
        description="End date period",
        examples=["2026-01-31"]
    ),
    granularity: Granularity = Query(
        default=Granularity.DAY,
        description="Aggregation level: day, week, month"
    ),
    db: AsyncSession = Depends(get_db),
) -> RevenueTrend:
    """
    Get revenue time series untuk chart.
    
    Return array data points, satu per hari/minggu/bulan sesuai granularity.
    Cocok untuk line chart di dashboard.
    
    - **granularity=day**: cocok untuk period < 90 hari
    - **granularity=week**: cocok untuk period 3-12 bulan
    - **granularity=month**: cocok untuk period > 1 tahun
    """

    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail=f"end_date ({end_date} cannot be before start_date ({start_date}))"
        )

    days_diff = (end_date - start_date).days
    if days_diff > 730:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum range 2 years (730 days). Your range: {days_diff} days"
        )
    return await get_revenue_trend(db, start_date, end_date, granularity)

@router.get(
    "/by-channel",
    response_model=RevenueByChannel,
    summary="Get revenue breakdown by traffic channel"
)
async def revenue_by_channel(
    start_date: date = Query(
        default_factory=lambda: date.today() - timedelta(days=30),
        description="Start poriod"
    ),
    end_date: date = Query(
        default_factory=lambda: date.today(),
        description="End poriod"
    ),
    limit : int | None = Query(
        default=None,
        description="Limiting total channel",
        ge=1,
        le=50
    ),
    db: AsyncSession = Depends(get_db)
) -> RevenueByChannel:
    """
    Get revenue breakdown per traffic channel.
    
    Menampilkan kontribusi setiap channel (Paid Social, Organic Search, dll)
    terhadap total revenue. Cocok untuk pie chart atau bar chart.
    
    - **percentage** = share revenue dari total (0-100)
    - Channels di-sort dari revenue terbesar
    - Kalau pakai `limit`, total tetap dihitung dari semua channel
    """
    
    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail=f"end_date ({end_date}) tidak boleh sebelum start_date ({start_date})",
        )
    
    days_diff = (end_date - start_date).days
    if days_diff > 730:
        raise HTTPException(
            status_code=400,
            detail=f"Range maksimum 2 tahun (730 hari). Range kamu: {days_diff} hari",
        )
    
    return await get_revenue_by_channel(db, start_date, end_date, limit)

@router.get(
    "/yearly-comparison",
    response_model=YearlyRevenueComparison,
    summary="Get yearly revenue comparison (current vs previous year)",
)
async def revenue_yearly_comparison(
    db: AsyncSession = Depends(get_db),
) -> YearlyRevenueComparison:
    """
    Get revenue per bulan untuk 2 tahun (current + previous).
    
    Widget ini standalone — tidak ikut filter date range.
    Cocok untuk visualisasi Year-over-Year (YoY) comparison.
    """
    return await get_yearly_revenue_comparison(db)