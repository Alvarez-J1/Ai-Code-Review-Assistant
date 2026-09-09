from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.diff import DiffHunk, FileChangeStatus, LineRange


class PreprocessingConfig(BaseModel):
    max_diff_lines_per_chunk: int = Field(default=120, ge=1)
    max_chunk_chars: int = Field(default=12_000, ge=1)
    large_diff_bytes: int = Field(default=100_000, ge=1)
    significant_source_change_lines: int = Field(default=25, ge=1)


class SkippedFile(BaseModel):
    file_path: str
    reason: str


class ReviewChunk(BaseModel):
    chunk_id: str
    file_path: str
    old_path: str | None = None
    status: FileChangeStatus
    language: str | None = None
    extension: str | None = None
    hunks: list[DiffHunk]
    changed_line_ranges: list[LineRange] = Field(default_factory=list)
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    additions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)
    diff_text: str
    is_large: bool = False


class PreprocessingResult(BaseModel):
    chunks: list[ReviewChunk] = Field(default_factory=list)
    skipped_files: list[SkippedFile] = Field(default_factory=list)
    is_large_diff: bool = False
    files_considered: int = Field(default=0, ge=0)
    files_reviewed: int = Field(default=0, ge=0)
