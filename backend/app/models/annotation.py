from datetime import datetime
from sqlalchemy import Date, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class Annotation(Base):
    """
    Annotation = event penting yang di-mark di dashboard timeline.
    
    Contoh: campaign launch, product release, incident, dll.
    Muncul sebagai vertical line di chart untuk membantu interpretasi trend.
    """

    __tablename__="annotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="other",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Annotation(id={self.id}, date={self.date}, title={self.title!r})>"