"""create review tables

Revision ID: 20260909_0001
Revises:
Create Date: 2026-09-09 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260909_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "review_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("repository_owner", sa.String(length=255), nullable=True),
        sa.Column("repository_name", sa.String(length=255), nullable=True),
        sa.Column("pull_request_number", sa.Integer(), nullable=True),
        sa.Column("pull_request_title", sa.String(length=500), nullable=True),
        sa.Column("pull_request_url", sa.String(length=1000), nullable=True),
        sa.Column("pull_request_state", sa.String(length=50), nullable=True),
        sa.Column("pull_request_author", sa.String(length=255), nullable=True),
        sa.Column("base_ref", sa.String(length=255), nullable=True),
        sa.Column("head_ref", sa.String(length=255), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("files_reviewed", sa.Integer(), nullable=False),
        sa.Column("total_findings", sa.Integer(), nullable=False),
        sa.Column("high_severity_count", sa.Integer(), nullable=False),
        sa.Column("medium_severity_count", sa.Integer(), nullable=False),
        sa.Column("low_severity_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_sessions_created_at", "review_sessions", ["created_at"])
    op.create_index("ix_review_sessions_input_type", "review_sessions", ["input_type"])
    op.create_index("ix_review_sessions_repo_pr", "review_sessions", ["repository_owner", "repository_name", "pull_request_number"])
    op.create_index("ix_review_sessions_repository_owner", "review_sessions", ["repository_owner"])
    op.create_index("ix_review_sessions_risk_level", "review_sessions", ["risk_level"])

    op.create_table(
        "review_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_order", sa.Integer(), nullable=False),
        sa.Column("file", sa.String(length=1000), nullable=False),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["review_session_id"], ["review_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_findings_category", "review_findings", ["category"])
    op.create_index("ix_review_findings_file", "review_findings", ["file"])
    op.create_index("ix_review_findings_location", "review_findings", ["review_session_id", "file", "line"])
    op.create_index("ix_review_findings_review_session_id", "review_findings", ["review_session_id"])
    op.create_index("ix_review_findings_severity", "review_findings", ["severity"])
    op.create_index("ix_review_findings_source", "review_findings", ["source"])


def downgrade() -> None:
    op.drop_index("ix_review_findings_source", table_name="review_findings")
    op.drop_index("ix_review_findings_severity", table_name="review_findings")
    op.drop_index("ix_review_findings_review_session_id", table_name="review_findings")
    op.drop_index("ix_review_findings_location", table_name="review_findings")
    op.drop_index("ix_review_findings_file", table_name="review_findings")
    op.drop_index("ix_review_findings_category", table_name="review_findings")
    op.drop_table("review_findings")
    op.drop_index("ix_review_sessions_risk_level", table_name="review_sessions")
    op.drop_index("ix_review_sessions_repository_owner", table_name="review_sessions")
    op.drop_index("ix_review_sessions_repo_pr", table_name="review_sessions")
    op.drop_index("ix_review_sessions_input_type", table_name="review_sessions")
    op.drop_index("ix_review_sessions_created_at", table_name="review_sessions")
    op.drop_table("review_sessions")
