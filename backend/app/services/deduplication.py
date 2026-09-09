from __future__ import annotations

import re

from app.schemas.review import ReviewFinding, Severity


_SEVERITY_RANK = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
}


def deduplicate_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    deduplicated: list[ReviewFinding] = []

    for finding in findings:
        duplicate_index = _find_duplicate_index(deduplicated, finding)
        if duplicate_index is None:
            deduplicated.append(finding)
            continue

        existing = deduplicated[duplicate_index]
        if _preference_score(finding) > _preference_score(existing):
            deduplicated[duplicate_index] = finding

    return deduplicated


def sort_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    return sorted(
        findings,
        key=lambda finding: (
            -_SEVERITY_RANK[finding.severity],
            finding.file,
            finding.line or 10**9,
            finding.category,
            finding.title.lower(),
        ),
    )


def _find_duplicate_index(existing_findings: list[ReviewFinding], candidate: ReviewFinding) -> int | None:
    for index, existing in enumerate(existing_findings):
        if _is_duplicate(existing, candidate):
            return index
    return None


def _is_duplicate(left: ReviewFinding, right: ReviewFinding) -> bool:
    if left.file != right.file or left.category != right.category:
        return False
    if not _ranges_overlap(left, right):
        return False
    return _text_similarity(left.title, right.title) >= 0.55 or _text_similarity(left.explanation, right.explanation) >= 0.55


def _ranges_overlap(left: ReviewFinding, right: ReviewFinding) -> bool:
    if left.line is None or right.line is None:
        return left.line is None and right.line is None

    left_start, left_end = left.line, left.end_line or left.line
    right_start, right_end = right.line, right.end_line or right.line
    return left_start <= right_end and right_start <= left_end


def _text_similarity(left: str, right: str) -> float:
    left_tokens = _normalized_tokens(left)
    right_tokens = _normalized_tokens(right)
    if not left_tokens or not right_tokens:
        return 0
    overlap = len(left_tokens & right_tokens)
    return overlap / len(left_tokens | right_tokens)


def _normalized_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    return {token for token in tokens if len(token) > 2}


def _preference_score(finding: ReviewFinding) -> tuple[int, float, int, int]:
    has_line = 1 if finding.line is not None else 0
    range_width = 0
    if finding.line is not None and finding.end_line is not None:
        range_width = max(0, finding.end_line - finding.line)
    specificity = has_line * 10 - range_width
    detail = len(finding.explanation) + len(finding.suggestion)
    return (_SEVERITY_RANK[finding.severity], finding.confidence, specificity, detail)
