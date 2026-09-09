from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.reviews import PersistenceError, get_review, list_reviews, persist_review
from app.db.session import get_db_session
from app.schemas.review import GitHubPRMetadata, ReviewInputType, ReviewListResponse, ReviewResponse
from app.services.diff_parser import DiffParseError
from app.services.github import (
    GitHubClient,
    GitHubError,
    InvalidGitHubPRError,
    normalize_github_pr_to_parsed_diff,
)
from app.services.review_pipeline import ReviewPipeline


router = APIRouter(prefix="/reviews", tags=["reviews"])


class DiffReviewRequest(BaseModel):
    diff: str = Field(min_length=1)


class GitHubReviewRequest(BaseModel):
    url: str = Field(min_length=1)


def get_review_pipeline() -> ReviewPipeline:
    return ReviewPipeline()


def get_github_client() -> GitHubClient:
    return GitHubClient()


@router.post("/diff", response_model=ReviewResponse, status_code=201)
async def review_pasted_diff(
    request: DiffReviewRequest,
    pipeline: ReviewPipeline = Depends(get_review_pipeline),
    db: Session = Depends(get_db_session),
) -> ReviewResponse:
    try:
        response = await pipeline.review_diff(request.diff)
    except DiffParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _persist_or_503(db, response, ReviewInputType.DIFF)


@router.post("/github", response_model=ReviewResponse, status_code=201)
async def review_github_pull_request(
    request: GitHubReviewRequest,
    pipeline: ReviewPipeline = Depends(get_review_pipeline),
    github_client: GitHubClient = Depends(get_github_client),
    db: Session = Depends(get_db_session),
) -> ReviewResponse:
    try:
        pull_request = await github_client.fetch_pull_request(request.url)
        parsed_diff = normalize_github_pr_to_parsed_diff(pull_request)
        response = await pipeline.review_parsed_diff(parsed_diff)
    except InvalidGitHubPRError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GitHubError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.public_message) from exc

    metadata = GitHubPRMetadata(
        owner=pull_request.reference.owner,
        repo=pull_request.reference.repo,
        pr_number=pull_request.reference.pr_number,
        title=pull_request.title,
        state=pull_request.state,
        author=pull_request.author,
        html_url=pull_request.reference.html_url,
        base_ref=pull_request.base_ref,
        head_ref=pull_request.head_ref,
        changed_files=pull_request.changed_files,
        additions=pull_request.additions,
        deletions=pull_request.deletions,
    )
    return _persist_or_503(db, response, ReviewInputType.GITHUB, metadata)


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review_by_id(review_id: UUID, db: Session = Depends(get_db_session)) -> ReviewResponse:
    try:
        response = get_review(db, review_id)
    except PersistenceError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc

    if response is None:
        raise HTTPException(status_code=404, detail="Review was not found")
    return response


@router.get("", response_model=ReviewListResponse)
def list_recent_reviews(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
) -> ReviewListResponse:
    try:
        return list_reviews(db, limit=limit, offset=offset)
    except PersistenceError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc


def _persist_or_503(
    db: Session,
    response: ReviewResponse,
    input_type: ReviewInputType,
    github_metadata: GitHubPRMetadata | None = None,
) -> ReviewResponse:
    try:
        return persist_review(db, response, input_type, github_metadata)
    except PersistenceError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
