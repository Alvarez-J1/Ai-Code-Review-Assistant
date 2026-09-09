from __future__ import annotations

from pathlib import PurePosixPath

from app.schemas.diff import ChangedFile, DiffHunk, DiffLine, DiffLineKind, LineRange, ParsedDiff
from app.schemas.preprocessing import PreprocessingConfig, PreprocessingResult, ReviewChunk, SkippedFile


LOCK_FILE_NAMES = {
    "bun.lock",
    "bun.lockb",
    "Cargo.lock",
    "composer.lock",
    "Gemfile.lock",
    "package-lock.json",
    "Pipfile.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
}

NON_REVIEWABLE_EXTENSIONS = {
    ".avif",
    ".bmp",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".webp",
    ".woff",
    ".woff2",
}


def prepare_review_chunks(
    parsed_diff: ParsedDiff,
    config: PreprocessingConfig | None = None,
) -> PreprocessingResult:
    config = config or PreprocessingConfig()
    chunks: list[ReviewChunk] = []
    skipped_files: list[SkippedFile] = []

    for changed_file in parsed_diff.files:
        reviewable, reason = _is_reviewable_file(changed_file)
        if not reviewable:
            skipped_files.append(SkippedFile(file_path=_display_path(changed_file), reason=reason))
            continue

        file_chunks = _chunks_for_file(changed_file, config)
        if not file_chunks:
            skipped_files.append(SkippedFile(file_path=_display_path(changed_file), reason="no reviewable hunks"))
            continue

        chunks.extend(file_chunks)

    reviewable_paths = {chunk.file_path for chunk in chunks}
    chunk_counts_by_file = {
        path: sum(1 for chunk in chunks if chunk.file_path == path)
        for path in reviewable_paths
    }
    was_split_for_size = any(count > 1 for count in chunk_counts_by_file.values())

    return PreprocessingResult(
        chunks=chunks,
        skipped_files=skipped_files,
        is_large_diff=parsed_diff.raw_size_bytes > config.large_diff_bytes or was_split_for_size,
        files_considered=len(parsed_diff.files),
        files_reviewed=len(reviewable_paths),
    )


def _is_reviewable_file(changed_file: ChangedFile) -> tuple[bool, str]:
    path = _display_path(changed_file)
    name = PurePosixPath(path).name

    if changed_file.is_binary:
        return False, "binary file"
    if changed_file.is_generated or name in LOCK_FILE_NAMES:
        return False, "generated or dependency file"
    if changed_file.extension in NON_REVIEWABLE_EXTENSIONS:
        return False, "non-reviewable file type"
    return True, ""


def _chunks_for_file(changed_file: ChangedFile, config: PreprocessingConfig) -> list[ReviewChunk]:
    partial_hunks: list[DiffHunk] = []
    for hunk in changed_file.hunks:
        partial_hunks.extend(_split_hunk(hunk, config))

    chunks: list[ReviewChunk] = []
    current_hunks: list[DiffHunk] = []
    current_line_count = 0
    current_chars = 0

    def flush() -> None:
        nonlocal current_hunks, current_line_count, current_chars
        if not current_hunks:
            return
        chunks.append(_build_chunk(changed_file, current_hunks, len(chunks) + 1, config))
        current_hunks = []
        current_line_count = 0
        current_chars = 0

    for hunk in partial_hunks:
        hunk_line_count = len(hunk.lines)
        hunk_chars = _hunk_char_count(hunk)
        would_exceed_lines = current_hunks and current_line_count + hunk_line_count > config.max_diff_lines_per_chunk
        would_exceed_chars = current_hunks and current_chars + hunk_chars > config.max_chunk_chars

        if would_exceed_lines or would_exceed_chars:
            flush()

        current_hunks.append(hunk)
        current_line_count += hunk_line_count
        current_chars += hunk_chars

    flush()
    return chunks


def _split_hunk(hunk: DiffHunk, config: PreprocessingConfig) -> list[DiffHunk]:
    if not hunk.lines:
        return []

    parts: list[DiffHunk] = []
    current_lines: list[DiffLine] = []
    current_chars = 0

    def flush() -> None:
        nonlocal current_lines, current_chars
        if not current_lines:
            return
        parts.append(_copy_hunk_with_lines(hunk, current_lines))
        current_lines = []
        current_chars = 0

    for line in hunk.lines:
        line_chars = len(line.content) + 2
        would_exceed_lines = current_lines and len(current_lines) >= config.max_diff_lines_per_chunk
        would_exceed_chars = current_lines and current_chars + line_chars > config.max_chunk_chars
        if would_exceed_lines or would_exceed_chars:
            flush()
        current_lines.append(line)
        current_chars += line_chars

    flush()
    return parts


def _copy_hunk_with_lines(original: DiffHunk, lines: list[DiffLine]) -> DiffHunk:
    old_lines = [line.old_line for line in lines if line.old_line is not None]
    new_lines = [line.new_line for line in lines if line.new_line is not None]
    old_count = sum(1 for line in lines if line.kind != DiffLineKind.ADDED)
    new_count = sum(1 for line in lines if line.kind != DiffLineKind.REMOVED)

    return DiffHunk(
        old_start=min(old_lines) if old_lines else original.old_start,
        old_count=old_count,
        new_start=min(new_lines) if new_lines else original.new_start,
        new_count=new_count,
        section_header=original.section_header,
        lines=lines.copy(),
    )


def _build_chunk(
    changed_file: ChangedFile,
    hunks: list[DiffHunk],
    sequence: int,
    config: PreprocessingConfig,
) -> ReviewChunk:
    file_path = _display_path(changed_file)
    changed_ranges = _changed_line_ranges(hunks)
    start_line = changed_ranges[0].start if changed_ranges else None
    end_line = changed_ranges[-1].end if changed_ranges else None
    additions = sum(1 for hunk in hunks for line in hunk.lines if line.kind == DiffLineKind.ADDED)
    deletions = sum(1 for hunk in hunks for line in hunk.lines if line.kind == DiffLineKind.REMOVED)
    diff_text = _format_chunk_diff(changed_file, hunks)

    return ReviewChunk(
        chunk_id=f"{file_path}:{sequence}",
        file_path=file_path,
        old_path=changed_file.old_path,
        status=changed_file.status,
        language=changed_file.language,
        extension=changed_file.extension,
        hunks=hunks,
        changed_line_ranges=changed_ranges,
        start_line=start_line,
        end_line=end_line,
        additions=additions,
        deletions=deletions,
        diff_text=diff_text,
        is_large=len(diff_text) > config.max_chunk_chars or len([line for hunk in hunks for line in hunk.lines]) > config.max_diff_lines_per_chunk,
    )


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


def _format_chunk_diff(changed_file: ChangedFile, hunks: list[DiffHunk]) -> str:
    file_path = _display_path(changed_file)
    lines = [
        f"File: {file_path}",
        f"Status: {changed_file.status}",
        f"Language: {changed_file.language or 'unknown'}",
        "Diff:",
    ]

    for hunk in hunks:
        section = f" {hunk.section_header}" if hunk.section_header else ""
        lines.append(f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@{section}")
        for diff_line in hunk.lines:
            prefix = {
                DiffLineKind.ADDED: "+",
                DiffLineKind.REMOVED: "-",
                DiffLineKind.CONTEXT: " ",
            }[diff_line.kind]
            line_number = diff_line.new_line if diff_line.new_line is not None else diff_line.old_line
            rendered_line = f"{prefix}{diff_line.content}"
            lines.append(f"{line_number or '-'}: {rendered_line}")

    return "\n".join(lines)


def _hunk_char_count(hunk: DiffHunk) -> int:
    return sum(len(line.content) + 2 for line in hunk.lines)


def _display_path(changed_file: ChangedFile) -> str:
    return changed_file.new_path or changed_file.old_path or "<unknown>"
