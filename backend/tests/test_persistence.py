from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.db.reviews import PersistenceError, get_review, list_reviews, persist_review
from app.models.review import ReviewFindingModel, ReviewSessionModel
from app.schemas.review import (
    FindingCategory,
    FindingSource,
    GitHubPRMetadata,
    ReviewFinding,
    ReviewInputType,
    ReviewResponse,
    ReviewStats,
    RiskLevel,
    Severity,
)


def test_persist_review_creates_session_and_findings(db_session) -> None:
    response = _response()

    persisted = persist_review(db_session, response, ReviewInputType.DIFF)

    assert persisted.review_id == response.review_id
    assert persisted.findings[0].file == "src/app.py"
    assert db_session.query(ReviewSessionModel).count() == 1
    assert db_session.query(ReviewFindingModel).count() == 1


def test_persist_review_stores_github_metadata(db_session) -> None:
    metadata = GitHubPRMetadata(
        owner="openai",
        repo="example",
        pr_number=123,
        title="Improve review pipeline",
        html_url="https://github.com/openai/example/pull/123",
    )

    persisted = persist_review(db_session, _response(), ReviewInputType.GITHUB, metadata)
    listed = list_reviews(db_session, limit=10, offset=0)

    assert persisted.stats.findings == 1
    assert listed.items[0].repository_owner == "openai"
    assert listed.items[0].repository_name == "example"
    assert listed.items[0].pull_request_number == 123


def test_get_review_returns_persisted_review(db_session) -> None:
    response = persist_review(db_session, _response(), ReviewInputType.DIFF)

    retrieved = get_review(db_session, response.review_id)

    assert retrieved is not None
    assert retrieved.review_id == response.review_id
    assert retrieved.findings[0].source == FindingSource.DETERMINISTIC


def test_list_reviews_returns_recent_summaries(db_session) -> None:
    older = _response(created_at=datetime.now(UTC) - timedelta(days=1))
    newer = _response(created_at=datetime.now(UTC))
    persist_review(db_session, older, ReviewInputType.DIFF)
    persist_review(db_session, newer, ReviewInputType.DIFF)

    response = list_reviews(db_session, limit=1, offset=0)

    assert response.count == 1
    assert response.items[0].review_id == newer.review_id
    assert response.items[0].stats.findings == 1


def test_get_review_returns_none_for_unknown_review(db_session) -> None:
    assert get_review(db_session, uuid4()) is None


def test_persist_review_rolls_back_on_transaction_failure(db_session) -> None:
    response = _response()
    persist_review(db_session, response, ReviewInputType.DIFF)

    with pytest.raises(PersistenceError):
        persist_review(db_session, response, ReviewInputType.DIFF)

    assert db_session.query(ReviewSessionModel).count() == 1
    assert db_session.query(ReviewFindingModel).count() == 1


def _response(created_at: datetime | None = None) -> ReviewResponse:
    return ReviewResponse(
        review_id=uuid4(),
        risk_level=RiskLevel.MEDIUM,
        summary="Reviewed one file and found one issue.",
        stats=ReviewStats(files_reviewed=1, findings=1, high_severity=0, medium_severity=1, low_severity=0),
        findings=[
            ReviewFinding(
                file="src/app.py",
                line=12,
                category=FindingCategory.BUG,
                severity=Severity.MEDIUM,
                title="Possible null dereference",
                explanation="The changed code may dereference a missing value.",
                suggestion="Guard the value before reading from it.",
                confidence=0.86,
                source=FindingSource.DETERMINISTIC,
            )
        ],
        created_at=created_at or datetime.now(UTC),
    )
