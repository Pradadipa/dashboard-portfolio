from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum


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

class Granularity(str, Enum):
    """Level agregasi untuk time series data"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"

class RevenueTrendPoint(BaseModel):
    """Satu data point dalam time series revenue"""

    date: date = Field(
        ...,
        description="Date (for granuralit=day) or start date poeriod (wweek/month)",
        examples=["2026-01-01"],
    )
    net_sales: Decimal = Field(
        ...,
        description="Net sales for this period",
        examples=["5200.00"],
    )
    orders: int = Field(
        ...,
        description="Total orders for this period",
        ge=0,
        examples=[45]
    )

class RevenueTrend(BaseModel):
    """Response schema for revenue trend (time series)"""
    start_date: date = Field(..., description="Start date period")
    end_date: date= Field(..., description="End date period")
    granularity: Granularity = Field(..., description="Level aggregation date")
    date_points: list[RevenueTrendPoint] = Field(
        ...,
        description="Time series data, order by oldest date"
    )
    total_points: int = Field(
        ...,
        description="Total data point",
        ge=0,
    )