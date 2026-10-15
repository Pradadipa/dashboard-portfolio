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