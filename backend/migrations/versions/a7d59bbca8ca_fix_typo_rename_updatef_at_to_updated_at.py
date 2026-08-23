"""fix typo rename updatef_at to updated_at

Revision ID: a7d59bbca8ca
Revises: 1d42e7e928d0
Create Date: 2026-08-23 18:20:01.553762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d59bbca8ca'
down_revision: Union[str, Sequence[str], None] = '1d42e7e928d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename kolom typo ke nama yang benar
    op.alter_column(
        'annotations',
        'updatef_at',
        new_column_name='updated_at',
    )
    
    # Set default now() supaya INSERT dapat value otomatis
    op.alter_column(
        'annotations',
        'updated_at',
        server_default=sa.text('now()'),
    )
    
    # Backfill row existing yang updated_at nya NULL
    op.execute("UPDATE annotations SET updated_at = created_at WHERE updated_at IS NULL")


def downgrade() -> None:
    op.alter_column(
        'annotations',
        'updated_at',
        server_default=None,
    )
    op.alter_column(
        'annotations',
        'updated_at',
        new_column_name='updatef_at',
    )
