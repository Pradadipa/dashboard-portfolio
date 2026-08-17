from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.revenue import RevenueSummary, RevenueTrend, Granularity
from app.services.revenue_services import get_revenue_summary, get_revenue_trend

router =  APIRouter(prefix="/api/revenue", tags=["revenue"])

@router.get(
    "/summary",
    response_model=RevenueSummary,
    summary="Get revenue summary for specific period",
)
async def revenue_summary(
    start_date: date = Query(
        default_factory=lambda: date.today() - timedelta(days=30),
        description="Start date period (default: 30 days ago)",
        example=["2026-07-01"]
    ),
    end_date: date = Query(
            default_factory=lambda: date.today(),
            description="End date period (default: today)",
            example=["2026-07-31"]
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
        default_factory=lambda: date.today() - timedelta(days=30),
        description="Start date period (default: 30 days ago)",
        examples=["2026-01-01"]
    ),
    end_date: date = Query(
        default_factory=lambda: date.today(),
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