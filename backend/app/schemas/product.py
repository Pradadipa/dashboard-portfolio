from datetime import date as date_type
from decimal import Decimal
from pydantic import BaseModel, Field

class ProductSparklinePoint(BaseModel):
    date: date_type
    revenue: Decimal

class TopProduct(BaseModel):
    rank: int = Field(..., description="Ranking based on revenue", ge=1)
    product_id: int = Field(..., description="Shopify product id")
    product_name: str = Field(..., description="Product name")
    revenue: Decimal = Field(..., description="Total revenue", ge=0)
    units_sold: int = Field(..., description="Total unit sold", ge=0)
    sparkline: list[ProductSparklinePoint] = Field(
        default_factory=list,
        description="Dialy revenue for mini chart"
    )

class TopProductsResponse(BaseModel):
    """Response schema untuk top products endpoint."""
    
    start_date: date_type
    end_date: date_type
    products: list[TopProduct] = Field(..., description="Top products, sorted by revenue desc")
    total_products_count: int = Field(..., ge=0)
