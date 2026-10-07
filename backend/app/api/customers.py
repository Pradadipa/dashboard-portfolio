"""API endpoints untuk customers."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.customer import CustomerSummary
from app.services.customer_service import get_customer_summary

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