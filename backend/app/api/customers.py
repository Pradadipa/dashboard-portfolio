"""API endpoints untuk customers."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.customer import (
    CustomerSummary,
    CustomerRFM,
    TopCustomersResponse,
    AcquisitionTrend,
    CohortRetentionResponse,
    AcquisitionChannelQualityResponse,
    )
from app.services.customer_service import (
    get_cohort_retention,
    get_customer_summary,
    get_customer_rfm_segmentation,
    get_top_customers,
    get_acquisition_trend,
    get_acquisition_channel_quality,
    )

# Create a router for customer-related endpoints
router = APIRouter(prefix="/api/customers", tags=["customers"])

# Endpoint: GET /api/customers/summary
@router.get(
    "/summary",
    response_model=CustomerSummary,
    summary="Get customer summary for a given date range",
)
async def customer_summary(
    start_date: date = Query(
        ...,
        description="Start date for the summary (YYYY-MM-DD)",
        examples=["2026-07-01"],
    ),
    end_date: date = Query(
        ...,
        description="End date for the summary (YYYY-MM-DD)",
        examples=["2026-07-31"],
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a summary of customers within a specified date range.

    This endpoint returns the total number of unique customers, new customers,
    returning customers, average lifetime value (LTV), and repeat purchase rate (RPR)
    for the given date range.
    """
    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date tidak boleh sebelum start_date"
        )
    return await get_customer_summary(db, start_date, end_date)

@router.get(
    "/rfm",
    response_model=CustomerRFM,
    summary="Get RFM customer segmentation"
)
async def customer_rfm(
    db: AsyncSession = Depends(get_db)
) -> CustomerRFM:
    """
    Get RFM (Recency, Frequency, Monetary) customer segmentation.
    
    Returns 10 segment classifications:
    - Champions, Loyal, Cant Lose Them (top value)
    - At Risk, Potential Loyalists, Promising (growth opportunity)
    - New Customers, About to Sleep (mid)
    - Hibernating, Lost (low priority)
    
    Scoring uses hybrid approach:
    - R: Fixed buckets by days (0-90, 90-180, 180-365, 1-2yr, 2yr+)
    - F: Fixed buckets by orders count (1, 2, 3, 4-10, 11+)
    - M: NTILE(5) auto-balance berdasarkan amount_spent
    
    Endpoint standalone — tidak ikut date filter karena RFM
    melihat lifetime customer behavior.
    """
    return await get_customer_rfm_segmentation(db)

@router.get(
    "/top",
    response_model=TopCustomersResponse,
    summary="Get top customers by lifetime value with RFM segment"
)
async def customer_top(
    limit: int = Query(
        default=10,
        description="Jumlah top customers (max 50)",
        ge=1,
        le=50
    ),
    db: AsyncSession = Depends(get_db)
) -> TopCustomersResponse:
    """
    Get top N customers by lifetime value.
    
    Response includes:
    - Masked email untuk privacy
    - Lifetime value, orders count
    - Geographic info (country, province)
    - Cross-reference RFM segment
    """
    return await get_top_customers(db, limit)

@router.get(
    "/acquisition-trend",
    response_model=AcquisitionTrend,
    summary="Get customer acquisition trend over N months"
)
async def customer_acquisition_trend(
    months: int = Query(
        default=12,
        description="Jumlah bulan ke belakang",
        ge=1,
        le=36
    ),
    db: AsyncSession = Depends(get_db)
) -> AcquisitionTrend:
    """
    Get customer acquisition trend selama N bulan terakhir (default 12).
    
    Returns:
    - data_points: time series dengan new, returning, total active, repeat rate per bulan
    - context metrics: current month total, MoM change, current repeat rate
    """
    return await get_acquisition_trend(db, months)

@router.get(
    "/cohort-retention",
    response_model=CohortRetentionResponse,
    summary="Cohort retention matrix"
)
async def cohort_retention_endpoint(
    cohort_count: int = Query(12, ge=1, le=24, description="Jumlah cohort (bulan ke belakang)"),
    period_count: int = Query(6, ge=1, le=12, description="Jumlah periode retensi (bulan ke depan)"),
    db: AsyncSession = Depends(get_db)
) -> CohortRetentionResponse:
    """
    Get cohort retention matrix.
    
    Returns:
    - cohort_months: list of cohort months (YYYY-MM)
    - retention_matrix: 2D list with retention rates per cohort and period
    """
    return await get_cohort_retention(db, cohort_count, period_count)


@router.get(
    "/acquisition-channel-quality",
    response_model=AcquisitionChannelQualityResponse,
    summary="Channel quality by first-order attribution"
)
async def customer_acquisition_channel_quality(
    db: AsyncSession = Depends(get_db)
) -> AcquisitionChannelQualityResponse:
    """
    Analisis kualitas acquisition per channel.

    Scope: customers dengan first_purchase_at antara 180-90 hari sebelum report end.
    Scope ini guarantee M3 (90 hari) complete untuk semua customer dalam cohort,
    sehingga comparison antar channel fair.

    Returns per channel:
    - volume (new_customers, pct_of_total)
    - retention quality (repeat_by_m3_pct)
    - value (avg_projected_12mo_value = amount × 12/tenure_months)
    - health (hibernating_pct, konsisten dengan RFM R_score ≤ 2)

    Plus benchmark metric (avg_repeat_by_m3_pct) sebagai reference line di chart.

    Channel normalization MIRROR ga4.v_monthly_channel_conversion di schema.sql
    supaya konsisten dengan dashboard GA4.
    """
    return await get_acquisition_channel_quality(db)