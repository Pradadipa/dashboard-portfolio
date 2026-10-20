from datetime import datetime
from datetime import date as date_type
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class CustomerSummary(BaseModel):
    """
    Response schema untuk endpoint customer summary.
    
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
    total_customers: int = Field(
        ...,
        description="Jumlah unique customers dalam periode",
        ge=0,
        examples=[1234],
    )
    new_customers: int = Field(
        ...,
        description="Jumlah new customers dalam periode",
        ge=0,
        examples=[567],
    )
    returning_customers: int = Field(
        ...,
        description="Jumlah returning customers dalam periode",
        ge=0,
        examples=[667],
    )
    average_ltv: Decimal = Field(
        ...,
        description="Average LTV (Lifetime Value) per customer dalam periode",
        ge=0,
        examples=[123.45]
    )
    repeat_purchase_rate: Decimal = Field(
        ...,
        description="Repeat Purchase Rate (RPR) dalam periode",
        ge=0,
        le=100
    )
    currency: str = Field(
        default="USD",
        description="Currency code untuk nilai monetary",
        min_length=3,
        max_length=3
    )

class RFMSegment(BaseModel):
    """1 Segment dalam RFM analysis"""

    segment: str = Field(
        ...,
        description="Nama segment (Champions, Loyal, At Risk, dll)"
    )
    customer_count: int = Field(
        ...,
        description="Jumlah customer di segment ini",
        ge=0
    )
    avg_lifetime_value: Decimal = Field(
        ...,
        description="Average lifetime spend per customer segment",
        ge=0
    )
    total_lifetime_value: Decimal = Field(
        ...,
        description="Total lifetime spend semua customer di segment",
        ge=0
    )
    avg_orders: Decimal = Field(
        ...,
        description="Average jumlah order per customer di segment",
        ge=0
    )
    avg_days_since_order: int = Field(
        ...,
        description="Average days sejak order terakhir",
        ge=0
    )
    percentage: Decimal = Field(
        ...,
        description="% dari total active customers",
        ge=0,
        le=100
    )

class CustomerRFM(BaseModel):
    """Response schema untuk customer RFM segmentation."""
    
    reference_date: date_type = Field(
        ...,
        description="Tanggal reference untuk recency calculation (CURRENT_DATE)",
    )
    total_active_customers: int = Field(
        ...,
        description="Total customer dengan minimal 1 order",
        ge=0,
    )
    segments: list[RFMSegment] = Field(
        ...,
        description="List segment, sorted by priority order",
    )

class TopCustomer(BaseModel):
    """1 top customer dengan metrics dan RFM segment."""

    rank: int = Field(..., ge=1)
    customer_id: int
    display_name: str | None = None
    email_masked: str = Field(..., description="Email dengan masking privacy")
    lifetime_value: Decimal =  Field(..., ge=0)
    orders_count: int = Field(..., ge=0)
    first_purchase_at: date_type | None = None
    last_order_at: date_type | None = None
    days_since_last_order: int = Field(..., ge=0)
    country: str | None = None
    province: str | None = None
    rfm_segment: str = Field(..., description="RFM Segment classification")

class TopCustomersResponse(BaseModel):
    total_customers: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    customers: list[TopCustomer]

class AcquisitionTrenPoint(BaseModel):
    """1 bulan data acquisition trend."""

    month: str = Field(
        ...,
        description="Bulan dalam format YYYY-MM",
        examples=["2026-07"]
    )
    new_customers: int = Field(
        ...,
        description="Customer dengan first_purchase_at di bulan ini",
        ge=0
    )
    returning_customers: int = Field(
        ...,
        description="Customer dengan order di bulan ini tapi first_purchase sebelumnya",
        ge=0
    )
    total_active: int = Field(
        ...,
        description="New + Returning",
        ge=0
    )
    repeat_rate_percent: Decimal = Field(
        ...,
        description="% returning dari total active (0-100)",
        ge=0,
        le=100
    )

class AcquisitionTrend(BaseModel):
    """Response schema untuk customer acquisition trend over time."""

    start_month: str = Field(..., examples=["2025-01"])
    end_month: str = Field(..., examples=["2026-10"])
    data_points: list[AcquisitionTrenPoint] = Field(
        ...,
        description="Time series data per bulan"
    )

    # Period total
    total_new: int = Field(..., ge=0)
    total_returning:int = Field(..., ge=0)

    # context metrix
    current_month_total: int = Field(
        ...,
        description="Total active di bulan terakhir",
        ge=0
    )
    mom_change_percent: Decimal | None = Field(
        default=None,
        description="% change total active vs previous month"
    )
    current_repeat_rate: Decimal = Field(
        ...,
        ge=0,
        le=100,
        description="Repeat rate di bulan terakhir"
    )