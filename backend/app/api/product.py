"""API endpoints untuk products."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.product import TopProductsResponse
from app.services.product_service import get_top_products


router = APIRouter(prefix="/api/products", tags=["products"])


@router.get(
    "/top",
    response_model=TopProductsResponse,
    summary="Get top products by revenue dengan sparkline",
)
async def top_products(
    start_date: date = Query(
        default_factory=lambda: date.today() - timedelta(days=30),
        description="Tanggal mulai periode",
    ),
    end_date: date = Query(
        default_factory=date.today,
        description="Tanggal akhir periode",
    ),
    db: AsyncSession = Depends(get_db),
) -> TopProductsResponse:
    """
    Get top N products by revenue dalam periode tertentu.
    
    Setiap product include daily revenue trend untuk sparkline visualization.
    """
    
    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail=f"end_date ({end_date}) tidak boleh sebelum start_date ({start_date})",
        )
    
    if (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=400,
            detail="Range maksimum 1 tahun untuk top products",
        )
    
    return await get_top_products(db, start_date, end_date)