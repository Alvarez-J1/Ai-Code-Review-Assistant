from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from app.schemas.diff import (
    ChangedFile,
    DiffHunk,
    DiffLine,
    DiffLineKind,
    FileChangeStatus,
    LineRange,
    ParsedDiff,
)


class DiffParseError(ValueError):
    """Raised when input cannot be interpreted as a unified diff."""


_HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?P<section>.*)$"
)

_LANGUAGE_BY_EXTENSION = {
    ".css": "CSS",
    ".go": "Go",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".json": "JSON",
    ".kt": "Kotlin",
    ".md": "Markdown",
    ".php": "PHP",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sql": "SQL",
    ".swift": "Swift",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".yaml": "YAML",
    ".yml": "YAML",
}

_GENERATED_FILE_NAMES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "composer.lock",
}

_GENERATED_PATH_PARTS = {
    ".next",
    "build",
    "coverage",
    "dist",
    "generated",
    "node_modules",
    "vendor",
}


@dataclass
class _FileBuilder:
    old_path: str | None = None
    new_path: str | None = None
    status: FileChangeStatus = FileChangeStatus.MODIFIED
    is_binary: bool = False
    additions: int = 0
    deletions: int = 0
    hunks: list[DiffHunk] = field(default_factory=list)


def parse_unified_diff(raw_diff: str) -> ParsedDiff:
    """Parse a git unified diff into normalized review input models."""
    if not raw_diff or not raw_diff.strip():
        raise DiffParseError("diff input is empty")

    files: list[ChangedFile] = []
    current_file: _FileBuilder | None = None
    current_hunk: DiffHunk | None = None
    old_line_cursor = 0
    new_line_cursor = 0

    def finish_current_file() -> None:
        nonlocal current_file, current_hunk
        if current_file is None:
            return
        files.append(_finalize_file(current_file))
        current_file = None
        current_hunk = None

    for raw_line in raw_diff.splitlines():
        if raw_line.startswith("diff --git "):
            finish_current_file()
            old_path, new_path = _parse_diff_git_paths(raw_line)
            current_file = _FileBuilder(old_path=old_path, new_path=new_path)
            current_hunk = None
            continue

        if raw_line.startswith("--- "):
            if current_file is None:
                current_file = _FileBuilder()
            old_path = _parse_file_marker_path(raw_line)
            current_file.old_path = old_path
            if old_path is None:
                current_file.status = FileChangeStatus.ADDED
            continue

        if raw_line.startswith("+++ "):
            if current_file is None:
                current_file = _FileBuilder()
            new_path = _parse_file_marker_path(raw_line)
            current_file.new_path = new_path
            if new_path is None:
                current_file.status = FileChangeStatus.DELETED
            elif current_file.old_path is None:
                current_file.status = FileChangeStatus.ADDED
            continue

        if current_file is None:
            continue

        if raw_line.startswith("new file mode"):
            current_file.status = FileChangeStatus.ADDED
            continue

        if raw_line.startswith("deleted file mode"):
            current_file.status = FileChangeStatus.DELETED
            continue

        if raw_line.startswith("rename from "):
            current_file.status = FileChangeStatus.RENAMED
            current_file.old_path = _normalize_path(raw_line.removeprefix("rename from ").strip(), "a/")
            continue

        if raw_line.startswith("rename to "):
            current_file.status = FileChangeStatus.RENAMED
            current_file.new_path = _normalize_path(raw_line.removeprefix("rename to ").strip(), "b/")
            continue

        if raw_line.startswith("Binary files") or raw_line == "GIT binary patch":
            current_file.is_binary = True
            continue

        hunk_match = _HUNK_RE.match(raw_line)
        if hunk_match:
            current_hunk = DiffHunk(
                old_start=int(hunk_match.group("old_start")),
                old_count=int(hunk_match.group("old_count") or 1),
                new_start=int(hunk_match.group("new_start")),
                new_count=int(hunk_match.group("new_count") or 1),
                section_header=hunk_match.group("section").strip() or None,
            )
            current_file.hunks.append(current_hunk)
            old_line_cursor = current_hunk.old_start
            new_line_cursor = current_hunk.new_start
            continue

        if current_hunk is None:
            continue

        if raw_line == r"\ No newline at end of file":
            continue

        if raw_line.startswith("+"):
            current_hunk.lines.append(
                DiffLine(
                    kind=DiffLineKind.ADDED,
                    content=raw_line[1:],
                    old_line=None,
                    new_line=new_line_cursor,
                )
            )
            current_file.additions += 1
            new_line_cursor += 1
            continue

        if raw_line.startswith("-"):
            current_hunk.lines.append(
                DiffLine(
                    kind=DiffLineKind.REMOVED,
                    content=raw_line[1:],
                    old_line=old_line_cursor,
                    new_line=None,
                )
            )
            current_file.deletions += 1
            old_line_cursor += 1
            continue

        if raw_line.startswith(" "):
            current_hunk.lines.append(
                DiffLine(
                    kind=DiffLineKind.CONTEXT,
                    content=raw_line[1:],
                    old_line=old_line_cursor,
                    new_line=new_line_cursor,
                )
            )
            old_line_cursor += 1
            new_line_cursor += 1
            continue

        raise DiffParseError(f"unexpected diff line inside hunk: {raw_line!r}")

    finish_current_file()

    if not files:
        raise DiffParseError("no changed files found in diff")

    return ParsedDiff(
        files=files,
        raw_size_bytes=len(raw_diff.encode("utf-8")),
        total_additions=sum(file.additions for file in files),
        total_deletions=sum(file.deletions for file in files),
    )


def _parse_diff_git_paths(line: str) -> tuple[str | None, str | None]:
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        raise DiffParseError("invalid diff --git header") from exc

    if len(parts) < 4:
        raise DiffParseError("invalid diff --git header")

    return _normalize_path(parts[2], "a/"), _normalize_path(parts[3], "b/")


def _parse_file_marker_path(line: str) -> str | None:
    marker_path = line[4:].strip()
    if not marker_path:
        return None

    try:
        parts = shlex.split(marker_path)
    except ValueError as exc:
        raise DiffParseError("invalid file marker path") from exc

    path = parts[0] if parts else marker_path
    if path == "/dev/null":
        return None
    return _normalize_path(path, "a/") if line.startswith("--- ") else _normalize_path(path, "b/")


def _normalize_path(path: str | None, prefix: str) -> str | None:
    if path is None:
        return None
    normalized = path.replace("\\", "/").strip()
    if normalized == "/dev/null":
        return None
    if normalized.startswith(prefix):
        normalized = normalized[len(prefix) :]
    return normalized


def _finalize_file(file: _FileBuilder) -> ChangedFile:
    status = file.status
    if file.old_path is None and file.new_path is not None:
        status = FileChangeStatus.ADDED
    elif file.new_path is None and file.old_path is not None:
        status = FileChangeStatus.DELETED

    review_path = file.new_path or file.old_path
    extension = _detect_extension(review_path)

    return ChangedFile(
        old_path=file.old_path,
        new_path=file.new_path,
        status=status,
        extension=extension,
        language=_LANGUAGE_BY_EXTENSION.get(extension or ""),
        is_binary=file.is_binary,
        is_generated=_is_generated_path(review_path),
        additions=file.additions,
        deletions=file.deletions,
        changed_line_ranges=_changed_line_ranges(file.hunks),
        hunks=file.hunks,
    )


def _detect_extension(path: str | None) -> str | None:
    if not path:
        return None
    suffix = PurePosixPath(path).suffix.lower()
    return suffix or None


def _is_generated_path(path: str | None) -> bool:
    if not path:
        return False
    normalized = path.replace("\\", "/")
    name = PurePosixPath(normalized).name
    if name in _GENERATED_FILE_NAMES:
        return True
    parts = set(PurePosixPath(normalized).parts)
    return bool(parts & _GENERATED_PATH_PARTS)


def _changed_line_ranges(hunks: list[DiffHunk]) -> list[LineRange]:
    ranges: list[LineRange] = []
    start: int | None = None
    end: int | None = None

    def flush() -> None:
        nonlocal start, end
        if start is not None and end is not None:
            ranges.append(LineRange(start=start, end=end))
        start = None
        end = None

    for hunk in hunks:
        for line in hunk.lines:
            if line.kind != DiffLineKind.ADDED or line.new_line is None:
                flush()
                continue
            if start is None:
                start = line.new_line
                end = line.new_line
            elif end is not None and line.new_line == end + 1:
                end = line.new_line
            else:
                flush()
                start = line.new_line
                end = line.new_line
        flush()

    return ranges
