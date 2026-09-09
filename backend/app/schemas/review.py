from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FindingCategory(StrEnum):
    BUG = "bug"
    EDGE_CASE = "edge_case"
    SECURITY = "security"
    PERFORMANCE = "performance"
    READABILITY = "readability"
    TESTING = "testing"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FindingSource(StrEnum):
    AI = "ai"
    DETERMINISTIC = "deterministic"


class ReviewInputType(StrEnum):
    DIFF = "diff"
    GITHUB = "github"


class ReviewStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str = Field(min_length=1)
    line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    category: FindingCategory
    severity: Severity
    title: str = Field(min_length=3, max_length=180)
    explanation: str = Field(min_length=10)
    suggestion: str = Field(min_length=5)
    confidence: float = Field(ge=0, le=1)
    source: FindingSource = FindingSource.AI

    @model_validator(mode="after")
    def validate_line_range(self) -> "ReviewFinding":
        if self.line is not None and self.end_line is not None and self.end_line < self.line:
            raise ValueError("end_line must be greater than or equal to line")
        return self


class ReviewStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files_reviewed: int = Field(default=0, ge=0)
    findings: int = Field(default=0, ge=0)
    high_severity: int = Field(default=0, ge=0)
    medium_severity: int = Field(default=0, ge=0)
    low_severity: int = Field(default=0, ge=0)


class ReviewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_level: RiskLevel
    summary: str = Field(min_length=1)
    stats: ReviewStats


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_type: ReviewInputType
    diff: str | None = None
    github_pr_url: str | None = None

    @model_validator(mode="after")
    def require_matching_input(self) -> "ReviewRequest":
        if self.input_type == ReviewInputType.DIFF and not self.diff:
            raise ValueError("diff is required when input_type is diff")
        if self.input_type == ReviewInputType.GITHUB and not self.github_pr_url:
            raise ValueError("github_pr_url is required when input_type is github")
        return self


class GitHubPRMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str
    repo: str
    pr_number: int = Field(ge=1)
    title: str | None = None
    state: str | None = None
    author: str | None = None
    html_url: str
    base_ref: str | None = None
    head_ref: str | None = None
    changed_files: int | None = Field(default=None, ge=0)
    additions: int | None = Field(default=None, ge=0)
    deletions: int | None = Field(default=None, ge=0)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: UUID
    input_type: ReviewInputType | None = None
    github_metadata: GitHubPRMetadata | None = None
    risk_level: RiskLevel
    summary: str
    stats: ReviewStats
    findings: list[ReviewFinding]
    created_at: datetime


class ReviewSessionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: UUID
    input_type: ReviewInputType
    status: ReviewStatus
    repository_owner: str | None = None
    repository_name: str | None = None
    pull_request_number: int | None = None
    pull_request_title: str | None = None
    pull_request_url: str | None = None
    state: str | None = None
    risk_level: RiskLevel
    summary: str
    stats: ReviewStats
    created_at: datetime
    completed_at: datetime | None = None


class ReviewListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ReviewSessionSummary]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    count: int = Field(ge=0)


class AIReviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[ReviewFinding] = Field(default_factory=list)
