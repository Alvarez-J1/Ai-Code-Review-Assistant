from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReviewSessionModel(Base):
    __tablename__ = "review_sessions"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    input_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    repository_owner: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    repository_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pull_request_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pull_request_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pull_request_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    pull_request_state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pull_request_author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    head_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    files_reviewed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_severity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    medium_severity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_severity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    findings: Mapped[list[ReviewFindingModel]] = relationship(
        back_populates="review_session",
        cascade="all, delete-orphan",
        order_by="ReviewFindingModel.created_order",
    )

    __table_args__ = (
        Index("ix_review_sessions_repo_pr", "repository_owner", "repository_name", "pull_request_number"),
        Index("ix_review_sessions_created_at", "created_at"),
    )


class ReviewFindingModel(Base):
    __tablename__ = "review_findings"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    review_session_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("review_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_order: Mapped[int] = mapped_column(Integer, nullable=False)
    file: Mapped[str] = mapped_column(String(1000), nullable=False, index=True)
    line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    review_session: Mapped[ReviewSessionModel] = relationship(back_populates="findings")

    __table_args__ = (
        Index("ix_review_findings_location", "review_session_id", "file", "line"),
    )
