from datetime import date as date_type
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum


class RevenueSummary(BaseModel):
    """
    Response schema untuk endpoint revenue summary.
    
    Semua nilai monetary pakai Decimal untuk presisi (bukan float).
    """
    
    start_date: date_type = Field(
        ...,
        description="Tanggal mulai periode",
        examples=["2026-07-01"],
    )
    end_date: date_type = Field(
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

    date: date_type = Field(
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
    start_date: date_type = Field(..., description="Start date period")
    end_date: date_type = Field(..., description="End date period")
    granularity: Granularity = Field(..., description="Level aggregation date")
    data_points: list[RevenueTrendPoint] = Field(
        ...,
        description="Time series data, order by oldest date"
    )
    total_points: int = Field(
        ...,
        description="Total data point",
        ge=0,
    )

class ChannelRevenue(BaseModel):

    channel: str = Field(
        ...,
        description="Traffic channel name",
        examples=["Paid Social"]
    )
    orders: int = Field(
        ...,
        description="Total orders from this channel",
        ge=0 
    )
    revenue: Decimal = Field(
        ...,
        description="Total net revenue from this channel"
    )
    percentage: Decimal = Field(
        ...,
        description="Percentage from total revenue",
        ge=0,
        le=100
    )

class RevenueByChannel(BaseModel):
    start_date: date_type = Field(..., description="Start period")
    end_date: date_type = Field(..., description="End period")
    channel: list[ChannelRevenue] = Field(
        ...,
        description="Breakdown per channel, sort by desc"
    )
    total_revenue: Decimal = Field(
        ...,
        description="Total revenue from all channel"
    )
    total_order: int = Field(
        ...,
        description="Total order from all channel"
    )