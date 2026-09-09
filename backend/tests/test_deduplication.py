from app.schemas.review import FindingCategory, FindingSource, ReviewFinding, Severity
from app.services.deduplication import deduplicate_findings, sort_findings


def _finding(
    title: str,
    *,
    file: str = "src/app.py",
    line: int | None = 10,
    category: FindingCategory = FindingCategory.BUG,
    severity: Severity = Severity.MEDIUM,
    confidence: float = 0.8,
    source: FindingSource = FindingSource.AI,
) -> ReviewFinding:
    return ReviewFinding(
        file=file,
        line=line,
        category=category,
        severity=severity,
        title=title,
        explanation=f"{title} could cause incorrect behavior in this changed code path.",
        suggestion="Update the changed code to handle this case explicitly.",
        confidence=confidence,
        source=source,
    )


def test_exact_duplicates_keep_stronger_finding() -> None:
    low = _finding("Possible null dereference", severity=Severity.LOW, confidence=0.7)
    high = _finding("Possible null dereference", severity=Severity.HIGH, confidence=0.6)

    deduped = deduplicate_findings([low, high])

    assert deduped == [high]


def test_similar_wording_on_same_line_is_deduplicated() -> None:
    first = _finding("Possible null dereference")
    second = _finding("Null dereference possible", confidence=0.9)

    deduped = deduplicate_findings([first, second])

    assert len(deduped) == 1
    assert deduped[0] == second


def test_different_issues_on_same_line_are_kept() -> None:
    first = _finding("Possible null dereference")
    second = _finding("Wrong cache key used")

    deduped = deduplicate_findings([first, second])

    assert len(deduped) == 2


def test_findings_on_different_files_are_kept() -> None:
    first = _finding("Possible null dereference", file="src/app.py")
    second = _finding("Possible null dereference", file="src/worker.py")

    deduped = deduplicate_findings([first, second])

    assert len(deduped) == 2


def test_deterministic_and_ai_overlap_deduplicates() -> None:
    deterministic = _finding(
        "Potential hard-coded secret",
        category=FindingCategory.SECURITY,
        severity=Severity.HIGH,
        confidence=0.92,
        source=FindingSource.DETERMINISTIC,
    )
    ai = _finding(
        "Hard-coded secret committed",
        category=FindingCategory.SECURITY,
        severity=Severity.MEDIUM,
        confidence=0.84,
        source=FindingSource.AI,
    )

    deduped = deduplicate_findings([ai, deterministic])

    assert deduped == [deterministic]


def test_sort_findings_orders_by_severity_then_location() -> None:
    low = _finding("Low issue", severity=Severity.LOW, line=1)
    high = _finding("High issue", severity=Severity.HIGH, line=20)
    medium = _finding("Medium issue", severity=Severity.MEDIUM, line=5)

    assert sort_findings([low, high, medium]) == [high, medium, low]
