"""Add `file` to sourcetype enum.

Revision ID: 002
Revises: 001
Create Date: 2026-05-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE sourcetype ADD VALUE 'file'")


def downgrade() -> None:
    # PostgreSQL cannot drop enum labels safely if rows use them; keep enum value.
    pass
