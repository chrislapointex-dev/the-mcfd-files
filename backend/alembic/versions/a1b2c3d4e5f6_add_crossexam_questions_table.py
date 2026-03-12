"""add crossexam_questions table

Revision ID: a1b2c3d4e5f6
Revises: 1594fe9ae105
Create Date: 2026-03-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '1594fe9ae105'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Table already exists (created via create_all before migrations were in place).
    # Use IF NOT EXISTS so this is safe to run on both old and new deployments.
    op.execute("""
        CREATE TABLE IF NOT EXISTS crossexam_questions (
            id SERIAL NOT NULL,
            contradiction_id INTEGER NOT NULL,
            questions_text TEXT NOT NULL,
            style VARCHAR(50) NOT NULL DEFAULT 'cross-examination',
            generated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            model_used VARCHAR(100) NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(contradiction_id) REFERENCES contradictions (id) ON DELETE CASCADE
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_crossexam_contradiction_id
        ON crossexam_questions (contradiction_id)
    """)


def downgrade() -> None:
    op.drop_index('ix_crossexam_contradiction_id', table_name='crossexam_questions')
    op.drop_table('crossexam_questions')
