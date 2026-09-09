from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.db.reviews import get_review, persist_review
from app.db.session import SessionLocal
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


GITHUB_DEMO_ID = UUID("00000000-0000-4000-8000-000000000501")
DIFF_DEMO_ID = UUID("00000000-0000-4000-8000-000000000502")


def main() -> None:
    inserted = 0
    skipped = 0

    with SessionLocal() as db:
        for response, input_type, metadata in _demo_reviews():
            if get_review(db, response.review_id) is not None:
                skipped += 1
                continue
            persist_review(db, response, input_type, metadata)
            inserted += 1

    print(f"Demo seed complete: inserted={inserted} skipped={skipped}")
    print(f"GitHub demo review: {GITHUB_DEMO_ID}")
    print(f"Pasted diff demo review: {DIFF_DEMO_ID}")


def _demo_reviews() -> list[tuple[ReviewResponse, ReviewInputType, GitHubPRMetadata | None]]:
    created_at = datetime.now(UTC)
    github_metadata = GitHubPRMetadata(
        owner="demo-org",
        repo="payments-api",
        pr_number=42,
        title="[Demo] Harden checkout webhook handling",
        state="open",
        author="demo-reviewer",
        html_url="https://github.com/demo-org/payments-api/pull/42",
        base_ref="main",
        head_ref="feature/webhook-hardening",
        changed_files=4,
        additions=84,
        deletions=19,
    )

    github_review = ReviewResponse(
        review_id=GITHUB_DEMO_ID,
        input_type=ReviewInputType.GITHUB,
        github_metadata=github_metadata,
        risk_level=RiskLevel.HIGH,
        summary="[Demo] Reviewed four files and found high-risk webhook validation gaps plus follow-up testing work.",
        stats=ReviewStats(files_reviewed=4, findings=3, high_severity=1, medium_severity=1, low_severity=1),
        findings=[
            ReviewFinding(
                file="src/webhooks/stripe.py",
                line=74,
                end_line=83,
                category=FindingCategory.SECURITY,
                severity=Severity.HIGH,
                title="[Demo] Verify webhook signatures before parsing payloads",
                explanation="The handler reads and trusts the request body before verifying the provider signature, so forged webhook requests could trigger payment state changes.",
                suggestion="Validate the signature header against the raw request body before deserializing or applying any checkout updates.",
                confidence=0.94,
                source=FindingSource.DETERMINISTIC,
            ),
            ReviewFinding(
                file="src/checkout/service.py",
                line=128,
                category=FindingCategory.BUG,
                severity=Severity.MEDIUM,
                title="[Demo] Preserve declined-payment state transitions",
                explanation="The new branch can overwrite a declined payment with a pending state when webhook events arrive out of order.",
                suggestion="Compare event timestamps or use an explicit state transition table before updating the checkout record.",
                confidence=0.82,
                source=FindingSource.AI,
            ),
            ReviewFinding(
                file="tests/test_webhooks.py",
                line=None,
                category=FindingCategory.TESTING,
                severity=Severity.LOW,
                title="[Demo] Add replay attack coverage",
                explanation="The tests cover successful webhook delivery but do not exercise duplicate delivery or stale timestamp handling.",
                suggestion="Add regression tests for duplicate event IDs and old signature timestamps.",
                confidence=0.71,
                source=FindingSource.AI,
            ),
        ],
        created_at=created_at,
    )

    diff_review = ReviewResponse(
        review_id=DIFF_DEMO_ID,
        input_type=ReviewInputType.DIFF,
        github_metadata=None,
        risk_level=RiskLevel.MEDIUM,
        summary="[Demo] Reviewed a pasted diff and found maintainability and performance issues across two files.",
        stats=ReviewStats(files_reviewed=2, findings=3, high_severity=0, medium_severity=2, low_severity=1),
        findings=[
            ReviewFinding(
                file="frontend/app/reviews/page.tsx",
                line=31,
                category=FindingCategory.PERFORMANCE,
                severity=Severity.MEDIUM,
                title="[Demo] Avoid refetching unchanged review history",
                explanation="The page reloads the first review page after every filter interaction even though filtering is local UI state.",
                suggestion="Keep filtering in the client component and fetch additional pages only when pagination changes.",
                confidence=0.79,
                source=FindingSource.AI,
            ),
            ReviewFinding(
                file="backend/app/services/review_pipeline.py",
                line=96,
                end_line=103,
                category=FindingCategory.EDGE_CASE,
                severity=Severity.MEDIUM,
                title="[Demo] Handle empty review chunks explicitly",
                explanation="A diff containing only generated files can leave the pipeline with no chunks, which makes the resulting summary ambiguous.",
                suggestion="Return a clear completed review with zero findings and a summary that explains every file was filtered.",
                confidence=0.84,
                source=FindingSource.DETERMINISTIC,
            ),
            ReviewFinding(
                file="frontend/components/FindingsList.tsx",
                line=144,
                category=FindingCategory.READABILITY,
                severity=Severity.LOW,
                title="[Demo] Clarify confidence formatting",
                explanation="The confidence display is correct, but the formatting logic is embedded directly in the JSX.",
                suggestion="Move confidence formatting into a small helper if the card gains more calculated display fields.",
                confidence=0.66,
                source=FindingSource.AI,
            ),
        ],
        created_at=created_at,
    )

    return [
        (github_review, ReviewInputType.GITHUB, github_metadata),
        (diff_review, ReviewInputType.DIFF, None),
    ]


if __name__ == "__main__":
    main()
