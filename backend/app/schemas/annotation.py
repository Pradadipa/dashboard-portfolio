from datetime import datetime
from datetime import date as date_type
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class AnnotationCategory(str, Enum):
    CAMPAIGN = "campaign"
    PRODUCT = "product"
    INCIDENT = "incident"
    PROMOTION = "promotion"
    OTHER = "other"

class AnnotationCreate(BaseModel):
    date: date_type = Field(
        ...,
        description="Date event",
        examples=["2026-03-15"]
    )
    title: str = Field(
        ...,
        description="Title annotation",
        min_length=1,
        max_length=200,
        examples=["Black Friday campaign start"]
    )
    description: str | None = Field(
        default=None,
        description="Detail description (oprtional)",
        max_length=200,
        examples=["Launch 50% off promo untuk semua produk selama 3 hari"]
    )
    category: AnnotationCategory = Field(
        default=AnnotationCategory.OTHER,
        description="Category annotation"
    )
    created_by: str | None = Field(
        default=None,
        description="User who created the annotation",
        max_length=200,
        examples=["prada"]
    )

class AnnotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="unique identifier")
    date: date_type = Field(..., description="Event date")
    title: str = Field(..., description="annotation tittle")
    category: str = Field(..., description="Category")
    created_at: datetime = Field(..., description="What time this annotation created")
    created_by: str | None =  Field(None, description="User who create")
    updated_at: datetime = Field(...,  description="last updated")

class AnnotationList(BaseModel):
    annotations: list[AnnotationResponse] = Field(
        ...,
        description="Array of annotations"
    )
    total: int = Field(..., description="Total annotations", ge=0)