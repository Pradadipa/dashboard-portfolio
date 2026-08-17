from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class RevenueSummary(BaseModel):
    """
    Response schema untuk endpoint revenue summary.
    
    Semua nilai monetary pakai Decimal untuk presisi (bukan float).
    """
    
    start_date: date = Field(
        ...,
        description="Tanggal mulai periode",
        examples=["2026-07-01"],
    )
    end_date: date = Field(
        ...,
        description="Tanggal akhir periode",
        examples=["2026-07-31"],
    )
    total_orders: int = Field(
        ...,
        description="Jumlah unique orders dalam periode",
        ge=0,
        examples=[1234],
    )
    net_sales: Decimal = Field(
        ...,
        description="Total net sales (sales - returns)",
        examples=["123456.78"],
    )
    total_sales: Decimal = Field(
        ...,
        description="Gross sales sebelum returns",
        examples=["130000.00"],
    )
    total_returns: Decimal = Field(
        ...,
        description="Total returns (nilai absolut)",
        ge=0,
        examples=["6543.22"],
    )
    average_order_value: Decimal = Field(
        ...,
        description="AOV = net_sales / total_orders",
        ge=0,
        examples=["100.05"],
    )
    currency: str = Field(
        default="USD",
        description="Currency code ISO 4217",
        examples=["USD"],
        min_length=3,
        max_length=3,
    )