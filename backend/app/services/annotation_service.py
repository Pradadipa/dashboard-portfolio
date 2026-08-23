from datetime import date as date_type
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import Annotation
from app.schemas.annotation import AnnotationCreate

async def create_annotation(
        db: AsyncSession,
        payload: AnnotationCreate
) -> Annotation:
    """
    Bikin annotation baru di database.
    
    Args:
        db: Async database session
        payload: Data annotation dari user
    
    Returns:
        Annotation object yang sudah di-persist (dengan id, created_at, dll)
    """
    annotation =  Annotation(
        date=payload.date,
        title=payload.title,
        description=payload.description,
        category=payload.category.value,
        created_by=payload.created_by
    )

    db.add(annotation)

    await db.commit()

    await db.refresh(annotation)

    return annotation

async def get_annotation_by_id(
        db: AsyncSession,
        annotation_id: int,
) -> Annotation | None:
    """
    Ambil satu annotation by ID.
    
    Returns:
        Annotation object kalau ada, None kalau tidak ada.
    """

    return await db.get(Annotation, annotation_id)

async def list_annotations(
        db: AsyncSession,
        start_date: date_type | None = None,
        end_date: date_type | None = None,
        category: str | None = None
) -> tuple[list[Annotation],  int]:
    """
    List annotations dengan filter optional.
    
    Args:
        db: Async database session
        start_date: Filter annotations dari tanggal ini (inclusive)
        end_date: Filter annotations sampai tanggal ini (inclusive)
        category: Filter by category
    
    Returns:
        Tuple: (list annotations, total count)
    """
    query = select(Annotation)
    count_query = select(func.count(Annotation.id))

    if start_date is not None:
        query = query.where(Annotation.date >= start_date)
        count_query = count_query.where(Annotation.date >= start_date)

    if end_date is not None:
        query = query.where(Annotation.date <= end_date)
        count_query = count_query.where(Annotation.date <= end_date)

    if category is not None:
        query = query.where(Annotation.category == category)
        count_query = count_query.where(Annotation.category == category)

    query = query.order_by(Annotation.date.desc(),  Annotation.id.desc())

    result = await db.execute(query)
    annotations = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    return annotations, total