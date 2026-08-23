from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Import semua models supaya Alembic bisa detect
# HARUS di bawah class Base untuk hindari circular import
from app.models import annotation  # noqa: E402, F401