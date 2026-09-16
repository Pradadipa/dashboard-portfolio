from datetime import date as date_type
from decimal import Decimal
from pydantic import BaseModel, Field

class TopProduct(BaseModel):
    rank: int = Field(..., description="Ranking based on revenue", ge=1)
    product_id: int = Field(..., description="Shopify product id")
    product_name: str = Field(..., description="Product name")
    revenue: Decimal = Field(..., description="Total revenue", ge=0)
    units_sold: int = Field(..., description="Total unit sold", ge=0)
    previous_revenue: Decimal = Field(
        default=Decimal("0"),
        description="Revenue di periode sebelumnya (durasi sama)",
    )
    previous_units_sold: int = Field(
        default=0,
        description="Units sold di periode sebelumnya",
        ge=0,
    )
    revenue_change_percent: Decimal | None = Field(
        default=None,
        description="% change revenue vs previous period (null kalau previous = 0)",
    )
    units_change_percent: Decimal | None = Field(
        default=None,
        description="% change units vs previous period",
    )

class TopProductsResponse(BaseModel):
    """Response schema untuk top products endpoint."""
    
    start_date: date_type
    end_date: date_type
    products: list[TopProduct] = Field(..., description="Top products, sorted by revenue desc")
    total_products_count: int = Field(..., ge=0)
