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
        le=1,
        examples=[0.67]
    )
    currency: str = Field(
        ...,
        default="USD",
        description="Currency code untuk nilai monetary",
        min_length=3,
        max_length=3
    )