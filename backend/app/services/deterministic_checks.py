from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import PurePosixPath

from app.schemas.diff import DiffLine, DiffLineKind
from app.schemas.preprocessing import PreprocessingConfig, ReviewChunk
from app.schemas.review import FindingCategory, FindingSource, ReviewFinding, Severity


_CONSOLE_LOG_RE = re.compile(r"\bconsole\.log\s*\(")
_PYTHON_PRINT_RE = re.compile(r"(?<![\w.])print\s*\(")
_TODO_RE = re.compile(r"\b(TODO|FIXME)\b", re.IGNORECASE)
_BARE_EXCEPT_RE = re.compile(r"^\s*except\s*:\s*(?:#.*)?$")
_EXCEPT_LINE_RE = re.compile(r"^\s*except(?:\s+[\w.]+(?:\s+as\s+\w+)?)?\s*:\s*(?:#.*)?$")
_EMPTY_JS_CATCH_RE = re.compile(r"\bcatch\s*\([^)]*\)\s*\{\s*\}")
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret[_-]?key)\b\s*[:=]\s*['\"][A-Za-z0-9_\-./+=]{16,}['\"]"
)
_PASSWORD_ASSIGNMENT_RE = re.compile(r"(?i)\b(password|passwd|pwd)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]")
_PYTHON_FUNCTION_RE = re.compile(r"^(?P<indent>\s*)def\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")

_SOURCE_EXTENSIONS = {
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
}


def run_deterministic_checks(
    chunks: Sequence[ReviewChunk],
    config: PreprocessingConfig | None = None,
) -> list[ReviewFinding]:
    config = config or PreprocessingConfig()
    findings: list[ReviewFinding] = []

    for chunk in chunks:
        added_lines = _added_lines(chunk)
        findings.extend(_line_based_checks(chunk, added_lines))
        findings.extend(_python_exception_checks(chunk, added_lines))
        findings.extend(_large_python_function_checks(chunk, added_lines))

    missing_tests_finding = _missing_tests_check(chunks, config)
    if missing_tests_finding is not None:
        findings.append(missing_tests_finding)

    return findings


def _line_based_checks(chunk: ReviewChunk, added_lines: list[DiffLine]) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []

    for line in added_lines:
        content = line.content
        stripped = content.strip()
        if not stripped:
            continue

        if _CONSOLE_LOG_RE.search(content) and not _is_comment_only(stripped, chunk.extension):
            findings.append(
                _finding(
                    chunk,
                    line,
                    FindingCategory.READABILITY,
                    Severity.LOW,
                    "Debug console output committed",
                    "The changed code adds console.log output, which can leak noisy diagnostics into production logs or browser consoles.",
                    "Remove the debug statement or route it through an intentional logging abstraction.",
                    0.88,
                )
            )

        if chunk.extension == ".py" and _PYTHON_PRINT_RE.search(content) and not _is_comment_only(stripped, chunk.extension):
            findings.append(
                _finding(
                    chunk,
                    line,
                    FindingCategory.READABILITY,
                    Severity.LOW,
                    "Debug print statement committed",
                    "The changed Python code adds print output, which is usually inappropriate for production services.",
                    "Use structured logging when runtime diagnostics are needed, or remove the temporary output.",
                    0.86,
                )
            )

        if _contains_todo_comment(content, chunk.extension):
            findings.append(
                _finding(
                    chunk,
                    line,
                    FindingCategory.READABILITY,
                    Severity.LOW,
                    "TODO or FIXME added",
                    "The changed code introduces a TODO or FIXME, which may leave unfinished behavior in the review.",
                    "Resolve the follow-up now or link it to a tracked issue with enough context.",
                    0.78,
                )
            )

        if _PRIVATE_KEY_RE.search(content) or _SECRET_ASSIGNMENT_RE.search(content) or _PASSWORD_ASSIGNMENT_RE.search(content):
            findings.append(
                _finding(
                    chunk,
                    line,
                    FindingCategory.SECURITY,
                    Severity.HIGH,
                    "Potential hard-coded secret",
                    "The changed code appears to add a credential, token, password, or private-key marker directly to source control.",
                    "Move the secret into a secure secret manager or environment variable and rotate it if it has already been committed.",
                    0.92,
                )
            )

        if _EMPTY_JS_CATCH_RE.search(content):
            findings.append(
                _finding(
                    chunk,
                    line,
                    FindingCategory.BUG,
                    Severity.MEDIUM,
                    "Empty exception handler",
                    "The changed code catches an error and ignores it completely, which can hide failed work and make incidents hard to diagnose.",
                    "Handle the error, rethrow it, or log enough context for operators to understand the failure.",
                    0.84,
                )
            )

    return findings


def _python_exception_checks(chunk: ReviewChunk, added_lines: list[DiffLine]) -> list[ReviewFinding]:
    if chunk.extension != ".py":
        return []

    findings: list[ReviewFinding] = []
    for index, line in enumerate(added_lines):
        stripped = line.content.strip()
        if _BARE_EXCEPT_RE.match(line.content):
            findings.append(
                _finding(
                    chunk,
                    line,
                    FindingCategory.BUG,
                    Severity.MEDIUM,
                    "Bare except catches too much",
                    "The changed code uses a bare except, which also catches interrupts and system-exiting exceptions.",
                    "Catch the specific exception type that the code can actually recover from.",
                    0.9,
                )
            )

        if _EXCEPT_LINE_RE.match(line.content):
            next_code_line = _next_non_empty_added_line(added_lines, index + 1)
            if next_code_line is not None and next_code_line.content.strip() == "pass":
                findings.append(
                    _finding(
                        chunk,
                        line,
                        FindingCategory.BUG,
                        Severity.MEDIUM,
                        "Empty exception handler",
                        "The changed code catches an exception and then only passes, which can silently suppress real failures.",
                        "Handle the exception, re-raise it, or log enough context to make the failure observable.",
                        0.87,
                    )
                )

        if stripped.startswith("except Exception") and "# noqa" not in line.content and "# intentional" not in line.content.lower():
            findings.append(
                _finding(
                    chunk,
                    line,
                    FindingCategory.READABILITY,
                    Severity.LOW,
                    "Broad exception handler",
                    "The changed code catches Exception broadly, which can hide unrelated programming or runtime errors.",
                    "Catch a narrower exception type or document why this broad handler is safe.",
                    0.72,
                )
            )

    return findings


def _large_python_function_checks(chunk: ReviewChunk, added_lines: list[DiffLine]) -> list[ReviewFinding]:
    if chunk.extension != ".py":
        return []

    findings: list[ReviewFinding] = []
    active_function_line: DiffLine | None = None
    active_indent = 0
    active_count = 0
    threshold = 80

    def flush() -> None:
        nonlocal active_function_line, active_indent, active_count
        if active_function_line is not None and active_count > threshold:
            findings.append(
                _finding(
                    chunk,
                    active_function_line,
                    FindingCategory.READABILITY,
                    Severity.MEDIUM,
                    "Large newly added function",
                    "The changed code adds a large Python function, which may be difficult to review, test, and maintain as a single unit.",
                    "Split the function around clear responsibilities before this grows harder to change.",
                    0.7,
                    end_line=(active_function_line.new_line or 0) + active_count - 1,
                )
            )
        active_function_line = None
        active_indent = 0
        active_count = 0

    for line in added_lines:
        match = _PYTHON_FUNCTION_RE.match(line.content)
        indent = len(line.content) - len(line.content.lstrip(" "))
        if match:
            flush()
            active_function_line = line
            active_indent = len(match.group("indent"))
            active_count = 1
            continue
        if active_function_line is not None:
            if line.content.strip() and indent <= active_indent and not line.content.startswith(" " * (active_indent + 1)):
                flush()
            else:
                active_count += 1

    flush()
    return findings


def _missing_tests_check(
    chunks: Sequence[ReviewChunk],
    config: PreprocessingConfig,
) -> ReviewFinding | None:
    source_chunks = [
        chunk
        for chunk in chunks
        if chunk.extension in _SOURCE_EXTENSIONS and not _is_test_file(chunk.file_path)
    ]
    if not source_chunks:
        return None

    has_test_changes = any(_is_test_file(chunk.file_path) for chunk in chunks)
    if has_test_changes:
        return None

    changed_lines = sum(chunk.additions + chunk.deletions for chunk in source_chunks)
    if changed_lines < config.significant_source_change_lines:
        return None

    primary_chunk = source_chunks[0]
    return ReviewFinding(
        file=primary_chunk.file_path,
        line=primary_chunk.start_line,
        category=FindingCategory.TESTING,
        severity=Severity.MEDIUM,
        title="Significant source change without tests",
        explanation="The diff changes a meaningful amount of source code, but no test file changes were detected.",
        suggestion="Add or update focused tests that cover the changed behavior.",
        confidence=0.74,
        source=FindingSource.DETERMINISTIC,
    )


def _finding(
    chunk: ReviewChunk,
    line: DiffLine,
    category: FindingCategory,
    severity: Severity,
    title: str,
    explanation: str,
    suggestion: str,
    confidence: float,
    end_line: int | None = None,
) -> ReviewFinding:
    return ReviewFinding(
        file=chunk.file_path,
        line=line.new_line,
        end_line=end_line,
        category=category,
        severity=severity,
        title=title,
        explanation=explanation,
        suggestion=suggestion,
        confidence=confidence,
        source=FindingSource.DETERMINISTIC,
    )


def _added_lines(chunk: ReviewChunk) -> list[DiffLine]:
    return [
        line
        for hunk in chunk.hunks
        for line in hunk.lines
        if line.kind == DiffLineKind.ADDED and line.new_line is not None
    ]


def _next_non_empty_added_line(lines: list[DiffLine], start_index: int) -> DiffLine | None:
    for line in lines[start_index:]:
        if line.content.strip() and not line.content.strip().startswith("#"):
            return line
    return None


def _is_comment_only(stripped: str, extension: str | None) -> bool:
    if extension == ".py":
        return stripped.startswith("#")
    return stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*")


def _contains_todo_comment(content: str, extension: str | None) -> bool:
    if extension == ".py":
        comment_index = content.find("#")
        return comment_index >= 0 and _TODO_RE.search(content[comment_index:]) is not None

    if extension in {".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".swift", ".kt", ".php", ".css"}:
        comment_markers = [content.find("//"), content.find("/*"), content.find("*")]
        comment_indexes = [index for index in comment_markers if index >= 0]
        return bool(comment_indexes and _TODO_RE.search(content[min(comment_indexes) :]))

    return _TODO_RE.search(content) is not None


def _is_test_file(path: str) -> bool:
    normalized = path.replace("\\", "/")
    parts = tuple(part.lower() for part in PurePosixPath(normalized).parts)
    name = PurePosixPath(normalized).name.lower()
    stem = PurePosixPath(normalized).stem.lower()

    return (
        "test" in parts
        or "tests" in parts
        or "__tests__" in parts
        or name.startswith("test_")
        or stem.endswith("_test")
        or ".test." in name
        or ".spec." in name
    )
