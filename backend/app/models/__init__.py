"""Central import untuk semua ORM models.

Alembic akan detect semua model yang di-import di sini.
Setiap model baru, tambahkan import-nya.
"""
from app.models.annotation import Annotation

__all__ = ["Annotation"]