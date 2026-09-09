from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.diff import ParsedDiff
from app.schemas.preprocessing import PreprocessingConfig
from app.schemas.review import ReviewFinding, ReviewResponse, ReviewStats, RiskLevel, Severity
from app.services.ai_reviewer import ChunkReviewer, OpenAIReviewer
from app.services.deduplication import deduplicate_findings, sort_findings
from app.services.deterministic_checks import run_deterministic_checks
from app.services.diff_parser import parse_unified_diff
from app.services.preprocessing import prepare_review_chunks


class ReviewPipeline:
    def __init__(
        self,
        ai_reviewer: ChunkReviewer | None = None,
        preprocessing_config: PreprocessingConfig | None = None,
    ) -> None:
        self.ai_reviewer = ai_reviewer or OpenAIReviewer()
        self.preprocessing_config = preprocessing_config or PreprocessingConfig()

    async def review_diff(self, raw_diff: str) -> ReviewResponse:
        parsed_diff = parse_unified_diff(raw_diff)
        return await self.review_parsed_diff(parsed_diff)

    async def review_parsed_diff(self, parsed_diff: ParsedDiff) -> ReviewResponse:
        prepared = prepare_review_chunks(parsed_diff, self.preprocessing_config)

        deterministic_findings = run_deterministic_checks(prepared.chunks, self.preprocessing_config)
        ai_findings: list[ReviewFinding] = []

        for chunk in prepared.chunks:
            try:
                ai_findings.extend(await self.ai_reviewer.review_chunk(chunk))
            except Exception:
                continue

        findings = sort_findings(deduplicate_findings(deterministic_findings + ai_findings))
        stats = _build_stats(prepared.files_reviewed, findings)
        risk_level = _calculate_risk_level(stats)

        return ReviewResponse(
            review_id=uuid4(),
            risk_level=risk_level,
            summary=_build_summary(risk_level, stats, skipped_count=len(prepared.skipped_files)),
            stats=stats,
            findings=findings,
            created_at=datetime.now(UTC),
        )


def _build_stats(files_reviewed: int, findings: list[ReviewFinding]) -> ReviewStats:
    return ReviewStats(
        files_reviewed=files_reviewed,
        findings=len(findings),
        high_severity=sum(1 for finding in findings if finding.severity == Severity.HIGH),
        medium_severity=sum(1 for finding in findings if finding.severity == Severity.MEDIUM),
        low_severity=sum(1 for finding in findings if finding.severity == Severity.LOW),
    )


def _calculate_risk_level(stats: ReviewStats) -> RiskLevel:
    if stats.high_severity:
        return RiskLevel.HIGH
    if stats.medium_severity:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _build_summary(risk_level: RiskLevel, stats: ReviewStats, skipped_count: int) -> str:
    if stats.files_reviewed == 0:
        return "No reviewable source changes were found after filtering generated, binary, or dependency files."

    if stats.findings == 0:
        return f"Reviewed {stats.files_reviewed} file(s) and found no likely issues in the changed code."

    skipped_note = f" {skipped_count} generated or non-reviewable file(s) were skipped." if skipped_count else ""
    return (
        f"Reviewed {stats.files_reviewed} file(s) and found {stats.findings} issue(s). "
        f"Overall risk is {risk_level.value} based on the highest-severity finding."
        f"{skipped_note}"
    )
