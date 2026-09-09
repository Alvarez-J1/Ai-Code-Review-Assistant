from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.review import ReviewFindingModel, ReviewSessionModel
from app.schemas.review import (
    GitHubPRMetadata,
    ReviewFinding,
    ReviewInputType,
    ReviewListResponse,
    ReviewResponse,
    ReviewSessionSummary,
    ReviewStats,
    ReviewStatus,
)


class PersistenceError(RuntimeError):
    pass


def persist_review(
    db: Session,
    response: ReviewResponse,
    input_type: ReviewInputType,
    github_metadata: GitHubPRMetadata | None = None,
) -> ReviewResponse:
    session = ReviewSessionModel(
        id=response.review_id,
        input_type=input_type.value,
        status=ReviewStatus.COMPLETED.value,
        repository_owner=github_metadata.owner if github_metadata else None,
        repository_name=github_metadata.repo if github_metadata else None,
        pull_request_number=github_metadata.pr_number if github_metadata else None,
        pull_request_title=github_metadata.title if github_metadata else None,
        pull_request_url=github_metadata.html_url if github_metadata else None,
        pull_request_state=github_metadata.state if github_metadata else None,
        pull_request_author=github_metadata.author if github_metadata else None,
        base_ref=github_metadata.base_ref if github_metadata else None,
        head_ref=github_metadata.head_ref if github_metadata else None,
        risk_level=response.risk_level.value,
        summary=response.summary,
        files_reviewed=response.stats.files_reviewed,
        total_findings=response.stats.findings,
        high_severity_count=response.stats.high_severity,
        medium_severity_count=response.stats.medium_severity,
        low_severity_count=response.stats.low_severity,
        created_at=response.created_at,
        completed_at=response.created_at,
        findings=[
            ReviewFindingModel(
                created_order=index,
                file=finding.file,
                line=finding.line,
                end_line=finding.end_line,
                category=finding.category.value,
                severity=finding.severity.value,
                title=finding.title,
                explanation=finding.explanation,
                suggestion=finding.suggestion,
                confidence=finding.confidence,
                source=finding.source.value,
            )
            for index, finding in enumerate(response.findings)
        ],
    )

    try:
        db.add(session)
        db.commit()
        db.refresh(session)
        return get_review(db, response.review_id) or response
    except SQLAlchemyError as exc:
        db.rollback()
        raise PersistenceError("Failed to persist review") from exc


def get_review(db: Session, review_id: UUID) -> ReviewResponse | None:
    try:
        session = db.scalar(
            select(ReviewSessionModel)
            .options(selectinload(ReviewSessionModel.findings))
            .where(ReviewSessionModel.id == review_id)
        )
    except SQLAlchemyError as exc:
        raise PersistenceError("Failed to retrieve review") from exc

    if session is None:
        return None
    return _session_to_response(session)


def list_reviews(db: Session, limit: int, offset: int) -> ReviewListResponse:
    try:
        sessions = list(
            db.scalars(
                select(ReviewSessionModel)
                .order_by(desc(ReviewSessionModel.created_at))
                .limit(limit)
                .offset(offset)
            )
        )
    except SQLAlchemyError as exc:
        raise PersistenceError("Failed to list reviews") from exc

    items = [_session_to_summary(session) for session in sessions]
    return ReviewListResponse(items=items, limit=limit, offset=offset, count=len(items))


def _session_to_response(session: ReviewSessionModel) -> ReviewResponse:
    return ReviewResponse(
        review_id=session.id,
        input_type=session.input_type,
        github_metadata=_session_github_metadata(session),
        risk_level=session.risk_level,
        summary=session.summary,
        stats=_session_stats(session),
        findings=[
            ReviewFinding(
                file=finding.file,
                line=finding.line,
                end_line=finding.end_line,
                category=finding.category,
                severity=finding.severity,
                title=finding.title,
                explanation=finding.explanation,
                suggestion=finding.suggestion,
                confidence=finding.confidence,
                source=finding.source,
            )
            for finding in session.findings
        ],
        created_at=session.created_at,
    )


def _session_to_summary(session: ReviewSessionModel) -> ReviewSessionSummary:
    return ReviewSessionSummary(
        review_id=session.id,
        input_type=session.input_type,
        status=session.status,
        repository_owner=session.repository_owner,
        repository_name=session.repository_name,
        pull_request_number=session.pull_request_number,
        pull_request_title=session.pull_request_title,
        pull_request_url=session.pull_request_url,
        state=session.pull_request_state,
        risk_level=session.risk_level,
        summary=session.summary,
        stats=_session_stats(session),
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


def _session_stats(session: ReviewSessionModel) -> ReviewStats:
    return ReviewStats(
        files_reviewed=session.files_reviewed,
        findings=session.total_findings,
        high_severity=session.high_severity_count,
        medium_severity=session.medium_severity_count,
        low_severity=session.low_severity_count,
    )


def _session_github_metadata(session: ReviewSessionModel) -> GitHubPRMetadata | None:
    if not (
        session.repository_owner
        and session.repository_name
        and session.pull_request_number
        and session.pull_request_url
    ):
        return None

    return GitHubPRMetadata(
        owner=session.repository_owner,
        repo=session.repository_name,
        pr_number=session.pull_request_number,
        title=session.pull_request_title,
        state=session.pull_request_state,
        author=session.pull_request_author,
        html_url=session.pull_request_url,
        base_ref=session.base_ref,
        head_ref=session.head_ref,
    )
