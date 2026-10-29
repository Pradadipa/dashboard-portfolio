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

class CohortRetentionCell(BaseModel):
    """Single cell dalam cohort retention matrix"""
    period_number: int = Field(..., description="Period relatif dari cohort month (1 = M+1, 2 = M+2, dst)")
    returners: int = Field(..., description="Jumlah customer dari cohort yang order di period ini")
    retention_pct: float | None = Field(
        None,
        description="Persentase retention. None jika period belum lengkap (future/current month)."
    )

class CohortRetentionRow(BaseModel):
    """Satu row cohort — satu bulan acquisition dengan retention per period."""
    cohort_month: date_type = Field(..., description="Bulan customer first purchase (first day of month)")
    cohort_size: int = Field(..., description="Jumlah total customer di cohort ini")
    cells: list[CohortRetentionCell] = Field(..., description="Retention cells dari M+1 sampai M+N")

class CohortRetentionResponse(BaseModel):
    """Response untuk endpoint cohort retention."""
    cohort_count: int = Field(..., description="Jumlah cohort yang dianalisis")
    period_count: int = Field(..., description="Jumlah period per cohort")
    rows: list[CohortRetentionRow] = Field(..., description="Cohort rows, oldest first (natural reading)")


class ChannelMetrics(BaseModel):
    """1 channel dengan metrics-nya untuk acquisition channel quality analysis."""

    channel: str = Field(
        ...,
        description="Nama channel (Paid Social, Email, Organic Search, dll)"
    )
    new_customers: int = Field(
        ...,
        description="Jumlah customer yang first purchase-nya via channel ini",
        ge=0
    )
    pct_of_total: Decimal = Field(
        ...,
        description="% share dari total new customers dalam cohort",
        ge=0,
        le=100
    )
    repeat_by_m3_pct: Decimal = Field(
        ...,
        description="% customer dari channel ini yang return (order kedua) dalam 90 hari dari first purchase",
        ge=0,
        le=100
    )
    avg_projected_12mo_value: Decimal = Field(
        ...,
        description="Projected 12-month LTV: amount_spent x (12 / tenure_months). "
                    "Over-projects untuk one-timer, tapi valid sebagai comparison antar channel.",
        ge=0
    )
    hibernating_pct: Decimal = Field(
        ...,
        description="% customer dari channel ini yang hibernating (last_order > 180 hari lalu). "
                    "Konsisten dengan RFM definition (R_score <= 2).",
        ge=0,
        le=100
    )


class AcquisitionChannelQualityResponse(BaseModel):
    """
    Response schema untuk Acquisition Channel Quality widget.

    Scope: customers dengan first_purchase_at antara 180-90 hari sebelum reference.
    Ini guarantee M3 (90 hari) complete untuk semua customer dalam cohort,
    sehingga comparison antar channel fair.
    """

    cohort_start: date_type = Field(
        ...,
        description="Awal periode cohort (reference - 180 hari)"
    )
    cohort_end: date_type = Field(
        ...,
        description="Akhir periode cohort (reference - 90 hari, exclusive)"
    )
    total_new_customers: int = Field(
        ...,
        description="Total new customers dalam cohort window",
        ge=0
    )
    avg_repeat_by_m3_pct: Decimal = Field(
        ...,
        description="Weighted average repeat-by-M3 across all channels, "
                    "dipakai sebagai benchmark line di chart",
        ge=0,
        le=100
    )
    top_channel: str = Field(
        ...,
        description="Channel dengan volume terbanyak"
    )
    top_channel_share: Decimal = Field(
        ...,
        description="% share top channel",
        ge=0,
        le=100
    )
    top_channel_repeat_rate: Decimal = Field(
        ...,
        description="Repeat-by-M3 % top channel (untuk headline insight)",
        ge=0,
        le=100
    )
    channels: list[ChannelMetrics] = Field(
        ...,
        description="List channel sorted by volume descending"
    )