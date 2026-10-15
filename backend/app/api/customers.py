"""API endpoints untuk customers."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.customer import CustomerSummary, CustomerRFM
from app.services.customer_service import get_customer_summary, get_customer_rfm_segmentation

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
    