from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.revenue import RevenueSummary
from app.services.revenue_services import get_revenue_summary

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