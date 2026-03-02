"""initial schema

Revision ID: e2fea8a3872b
Revises: 
Create Date: 2026-03-01 19:34:53.089224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2fea8a3872b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # DB already exists and matches the models — this revision marks the baseline.
    # The HNSW index on chunks.embedding is managed by app startup (main.py),
    # not by Alembic, so it is intentionally excluded here.
    pass


def downgrade() -> None:
    pass
