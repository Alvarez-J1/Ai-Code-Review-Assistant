from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, computed_field, field_validator


class FileChangeStatus(StrEnum):
    ADDED = "added"
    DELETED = "deleted"
    MODIFIED = "modified"
    RENAMED = "renamed"


class DiffLineKind(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    CONTEXT = "context"


class LineRange(BaseModel):
    start: int = Field(ge=1)
    end: int = Field(ge=1)

    @field_validator("end")
    @classmethod
    def end_must_not_precede_start(cls, end: int, info) -> int:
        start = info.data.get("start")
        if start is not None and end < start:
            raise ValueError("end must be greater than or equal to start")
        return end


class DiffLine(BaseModel):
    kind: DiffLineKind
    content: str
    old_line: int | None = Field(default=None, ge=1)
    new_line: int | None = Field(default=None, ge=1)


class DiffHunk(BaseModel):
    old_start: int = Field(ge=0)
    old_count: int = Field(ge=0)
    new_start: int = Field(ge=0)
    new_count: int = Field(ge=0)
    section_header: str | None = None
    lines: list[DiffLine] = Field(default_factory=list)

    @computed_field
    @property
    def added_lines(self) -> list[DiffLine]:
        return [line for line in self.lines if line.kind == DiffLineKind.ADDED]

    @computed_field
    @property
    def removed_lines(self) -> list[DiffLine]:
        return [line for line in self.lines if line.kind == DiffLineKind.REMOVED]

    @computed_field
    @property
    def context_lines(self) -> list[DiffLine]:
        return [line for line in self.lines if line.kind == DiffLineKind.CONTEXT]


class ChangedFile(BaseModel):
    old_path: str | None = None
    new_path: str | None = None
    status: FileChangeStatus = FileChangeStatus.MODIFIED
    extension: str | None = None
    language: str | None = None
    is_binary: bool = False
    is_generated: bool = False
    additions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)
    changed_line_ranges: list[LineRange] = Field(default_factory=list)
    hunks: list[DiffHunk] = Field(default_factory=list)

    @field_validator("new_path", "old_path")
    @classmethod
    def blank_paths_are_not_allowed(cls, path: str | None) -> str | None:
        if path is not None and not path.strip():
            raise ValueError("path cannot be blank")
        return path


class ParsedDiff(BaseModel):
    files: list[ChangedFile] = Field(default_factory=list)
    raw_size_bytes: int = Field(ge=0)
    total_additions: int = Field(default=0, ge=0)
    total_deletions: int = Field(default=0, ge=0)
