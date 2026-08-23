from datetime import date as date_type
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.annotation import (
    AnnotationCreate,
    AnnotationResponse,
    AnnotationCategory,
    AnnotationList
)
from app.services.annotation_service import (
    create_annotation,
    get_annotation_by_id,
    list_annotations
)

router = APIRouter(prefix="/api/annotations", tags=["annotations"])

@router.post(
    "",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new annotation"
)
async def create_annotation_endpoint(
    payload: AnnotationCreate,
    db: AsyncSession = Depends(get_db)
) -> AnnotationResponse:
    """
    Bikin annotation baru untuk mark event penting di timeline.
    
    **Categories:**
    - **campaign**: Marketing campaign (Black Friday, etc)
    - **product**: Product launch atau update
    - **incident**: Downtime, bug, atau masalah operasional
    - **promotion**: Diskon atau promo
    - **other**: Event lain
    """
    annotation = await create_annotation(db, payload)
    return annotation

@router.get(
    "",
    response_model=AnnotationList,
    summary="List annotations with filter"
)
async def list_annotations_endpoint(
    start_date: date_type | None = Query(
        default=None,
        description="Filter from this date. If empty, not filter"
    ),
    end_date: date_type | None = Query(
        default=None,
        description="Filter until this date. If empty, not filter"
    ),
    category: AnnotationCategory | None = Query(
        default=None,
        description="Filter by category"
    ),
    db: AsyncSession = Depends(get_db)
) -> AnnotationList:
    """
    List annotations dengan optional filter.
    
    Return terurut dari annotation terbaru ke terlama.
    Berguna untuk render vertical lines di chart timeline.
    """

    if start_date and end_date and end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail=f"end_date ({end_date}) tidak boleh sebelum start_date ({start_date})",
        )

    category_value = category.value if category else None

    annotations, total = await list_annotations(
        db,
        start_date=start_date,
        end_date=end_date,
        category=category_value
    )

    return AnnotationList(annotations=annotations, total=total)

@router.get(
    "/{annotation_id}",
    response_model=AnnotationResponse,
    summary="Get annotation by ID"
)
async def get_annotation_endpoint(
    annotation_id: int,
    db: AsyncSession = Depends(get_db)
) -> AnnotationResponse:
    annotation = await get_annotation_by_id(db, annotation_id)

    if annotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Annotation with id={annotation_id} not found"
        )
    return annotation