from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GitHubPRReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str = Field(min_length=1)
    repo: str = Field(min_length=1)
    pr_number: int = Field(ge=1)
    html_url: str


class GitHubChangedFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1)
    status: str = Field(min_length=1)
    additions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)
    changes: int = Field(default=0, ge=0)
    patch: str | None = None
    previous_filename: str | None = None


class GitHubPullRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: GitHubPRReference
    title: str | None = None
    state: str | None = None
    author: str | None = None
    base_ref: str | None = None
    head_ref: str | None = None
    additions: int | None = Field(default=None, ge=0)
    deletions: int | None = Field(default=None, ge=0)
    changed_files: int | None = Field(default=None, ge=0)
    files: list[GitHubChangedFile]
