from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.review import (
    FindingCategory,
    ReviewFinding,
    ReviewInputType,
    ReviewRequest,
    ReviewResponse,
    ReviewStats,
    RiskLevel,
    Severity,
)


def test_review_finding_validates_confidence_range() -> None:
    with pytest.raises(ValidationError):
        ReviewFinding(
            file="src/app.py",
            line=12,
            category=FindingCategory.BUG,
            severity=Severity.HIGH,
            title="Possible null dereference",
            explanation="The value may be None before its attribute is accessed.",
            suggestion="Guard the value before reading from it.",
            confidence=1.2,
        )


def test_review_finding_validates_line_order() -> None:
    with pytest.raises(ValidationError, match="end_line"):
        ReviewFinding(
            file="src/app.py",
            line=12,
            end_line=10,
            category=FindingCategory.BUG,
            severity=Severity.MEDIUM,
            title="Invalid range",
            explanation="The ending line should not precede the starting line.",
            suggestion="Use a valid inclusive range.",
            confidence=0.8,
        )


def test_review_request_requires_matching_diff_input() -> None:
    with pytest.raises(ValidationError, match="diff is required"):
        ReviewRequest(input_type=ReviewInputType.DIFF)

    request = ReviewRequest(input_type=ReviewInputType.DIFF, diff="diff --git a/a.py b/a.py")

    assert request.diff is not None


def test_review_response_accepts_structured_payload() -> None:
    response = ReviewResponse(
        review_id=uuid4(),
        risk_level=RiskLevel.MEDIUM,
        summary="The change is mostly sound but contains one likely runtime issue.",
        stats=ReviewStats(files_reviewed=1, findings=1, high_severity=0, medium_severity=1, low_severity=0),
        findings=[
            ReviewFinding(
                file="src/app.py",
                line=12,
                category=FindingCategory.BUG,
                severity=Severity.MEDIUM,
                title="Possible missing None guard",
                explanation="The changed code reads a value that may be None.",
                suggestion="Add a guard before accessing the value.",
                confidence=0.86,
            )
        ],
        created_at="2026-09-09T12:00:00Z",
    )

    assert response.stats.findings == 1
