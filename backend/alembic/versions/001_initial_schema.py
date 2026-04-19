"""Initial schema — all tables.

Revision ID: 001
Revises: None
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── projects ──
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("prompt", sa.Text, nullable=True),
        sa.Column("settings", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── sources ──
    source_type_enum = sa.Enum("web", "telegram", name="sourcetype")
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("source_type", source_type_enum, index=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("uri", sa.Text, nullable=True),
        sa.Column("settings", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── ingestion_jobs ──
    job_status_enum = sa.Enum("pending", "running", "done", "failed", name="ingestionjobstatus")
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("cron", sa.Text, nullable=False, server_default="*/30 * * * *"),
        sa.Column("status", job_status_enum, nullable=False, server_default="pending"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("last_run_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── source_chunks ──
    op.create_table(
        "source_chunks",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── embedding_records ──
    op.create_table(
        "embedding_records",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("chunk_id", sa.Integer, sa.ForeignKey("source_chunks.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False, server_default="stub-hash-32"),
        sa.Column("vector_size", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── vector_records ──
    op.create_table(
        "vector_records",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("chunk_id", sa.Integer, sa.ForeignKey("source_chunks.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("point_id", sa.String(128), unique=True, index=True, nullable=False),
        sa.Column("collection_name", sa.String(128), nullable=False, server_default="source_chunks"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── rag_query_logs ──
    op.create_table(
        "rag_query_logs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("retrieved_context", sa.JSON, nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── chat_logs ──
    op.create_table(
        "chat_logs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("sources", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("chat_logs")
    op.drop_table("rag_query_logs")
    op.drop_table("vector_records")
    op.drop_table("embedding_records")
    op.drop_table("source_chunks")
    op.drop_table("ingestion_jobs")
    op.drop_table("sources")
    op.drop_table("projects")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS sourcetype")
    op.execute("DROP TYPE IF EXISTS ingestionjobstatus")
