from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.reviews import get_github_client, get_review_pipeline
from app.db.session import get_db_session
from app.main import create_app
from app.schemas.github import GitHubChangedFile, GitHubPullRequest, GitHubPRReference
from app.schemas.review import FindingCategory, FindingSource, ReviewFinding, Severity
from app.services.github import GitHubNotFoundError
from app.services.review_pipeline import ReviewPipeline


class FakeReviewer:
    async def review_chunk(self, chunk):
        return [
            ReviewFinding(
                file=chunk.file_path,
                line=chunk.start_line,
                category=FindingCategory.BUG,
                severity=Severity.MEDIUM,
                title="Possible runtime issue",
                explanation="The mocked AI reviewer found a likely runtime problem.",
                suggestion="Handle the edge case before returning.",
                confidence=0.82,
                source=FindingSource.AI,
            )
        ]


class FakeGitHubClient:
    async def fetch_pull_request(self, url: str) -> GitHubPullRequest:
        return GitHubPullRequest(
            reference=GitHubPRReference(
                owner="openai",
                repo="example",
                pr_number=123,
                html_url="https://github.com/openai/example/pull/123",
            ),
            title="Improve review pipeline",
            state="open",
            author="octocat",
            base_ref="main",
            head_ref="feature/review",
            additions=1,
            deletions=0,
            changed_files=1,
            files=[
                GitHubChangedFile(
                    filename="src/app.py",
                    status="modified",
                    additions=1,
                    deletions=0,
                    changes=1,
                    patch="""@@ -1 +1,2 @@
 def run():
+    return None.value""",
                )
            ],
        )


class MissingGitHubClient:
    async def fetch_pull_request(self, url: str) -> GitHubPullRequest:
        raise GitHubNotFoundError()


class BrokenSession:
    def add(self, value):
        pass

    def commit(self):
        raise SQLAlchemyError("database down")

    def rollback(self):
        pass


class BrokenReadSession:
    def scalar(self, statement):
        raise SQLAlchemyError("database down")


def _client(db_session, github_client=None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_review_pipeline] = lambda: ReviewPipeline(ai_reviewer=FakeReviewer())
    app.dependency_overrides[get_db_session] = lambda: db_session
    if github_client is not None:
        app.dependency_overrides[get_github_client] = lambda: github_client
    return TestClient(app)


def test_review_diff_endpoint_returns_structured_response(db_session) -> None:
    raw_diff = """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
 def run():
+    return None.value
"""

    response = _client(db_session).post("/api/reviews/diff", json={"diff": raw_diff})

    assert response.status_code == 201
    body = response.json()
    assert body["risk_level"] == "medium"
    assert body["stats"]["files_reviewed"] == 1
    assert body["stats"]["findings"] == 1
    assert body["findings"][0]["source"] == "ai"

    get_response = _client(db_session).get(f"/api/reviews/{body['review_id']}")
    assert get_response.status_code == 200
    assert get_response.json()["review_id"] == body["review_id"]


def test_review_diff_endpoint_rejects_malformed_diff(db_session) -> None:
    response = _client(db_session).post("/api/reviews/diff", json={"diff": "not a git diff"})

    assert response.status_code == 422
    assert response.json()["detail"] == "no changed files found in diff"


def test_review_diff_endpoint_rejects_empty_diff(db_session) -> None:
    response = _client(db_session).post("/api/reviews/diff", json={"diff": ""})

    assert response.status_code == 422


def test_review_github_endpoint_returns_and_persists_structured_response(db_session) -> None:
    response = _client(db_session, github_client=FakeGitHubClient()).post(
        "/api/reviews/github",
        json={"url": "https://github.com/openai/example/pull/123"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["risk_level"] == "medium"

    list_response = _client(db_session).get("/api/reviews")
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["repository_owner"] == "openai"


def test_review_github_endpoint_rejects_malformed_url(db_session) -> None:
    response = _client(db_session).post("/api/reviews/github", json={"url": "https://gitlab.com/o/r/pull/1"})

    assert response.status_code == 422


def test_review_github_endpoint_translates_not_found(db_session) -> None:
    response = _client(db_session, github_client=MissingGitHubClient()).post(
        "/api/reviews/github",
        json={"url": "https://github.com/openai/example/pull/123"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "GitHub pull request was not found"


def test_get_review_returns_404_for_unknown_review(db_session) -> None:
    response = _client(db_session).get("/api/reviews/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404


def test_get_review_rejects_malformed_uuid(db_session) -> None:
    response = _client(db_session).get("/api/reviews/not-a-uuid")

    assert response.status_code == 422


def test_list_reviews_supports_pagination(db_session) -> None:
    raw_diff = """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
 def run():
+    return None.value
"""
    client = _client(db_session)
    client.post("/api/reviews/diff", json={"diff": raw_diff})
    client.post("/api/reviews/diff", json={"diff": raw_diff})

    response = client.get("/api/reviews?limit=1&offset=1")

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_review_diff_endpoint_returns_503_on_database_failure() -> None:
    raw_diff = """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
 def run():
+    return None.value
"""

    response = _client(BrokenSession()).post("/api/reviews/diff", json={"diff": raw_diff})

    assert response.status_code == 503
    assert response.json()["detail"] == "Database is unavailable"


def test_get_review_returns_503_on_database_failure() -> None:
    response = _client(BrokenReadSession()).get("/api/reviews/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 503
