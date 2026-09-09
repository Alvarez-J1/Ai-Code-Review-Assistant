import httpx
import pytest

from app.schemas.github import GitHubChangedFile, GitHubPullRequest, GitHubPRReference
from app.services.github import (
    GitHubClient,
    GitHubLargePRError,
    GitHubNetworkError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    InvalidGitHubPRError,
    normalize_github_pr_to_parsed_diff,
    parse_github_pr_url,
)
from app.services.preprocessing import prepare_review_chunks


def test_parse_valid_github_pr_url() -> None:
    reference = parse_github_pr_url("https://github.com/openai/example-repo/pull/123")

    assert reference.owner == "openai"
    assert reference.repo == "example-repo"
    assert reference.pr_number == 123


@pytest.mark.parametrize(
    "url",
    [
        "github.com/openai/example/pull/1",
        "https://gitlab.com/openai/example/pull/1",
        "https://github.com/openai/example",
        "https://github.com/openai/example/issues/1",
        "https://github.com/openai/example/pull/not-a-number",
        "https://github.com/openai/example/pull/0",
    ],
)
def test_parse_rejects_invalid_github_pr_urls(url: str) -> None:
    with pytest.raises(InvalidGitHubPRError):
        parse_github_pr_url(url)


@pytest.mark.asyncio
async def test_fetch_pull_request_without_authentication() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/repos/openai/example/pulls/123":
            return httpx.Response(200, json=_pr_payload())
        if request.url.path == "/repos/openai/example/pulls/123/files":
            return httpx.Response(200, json=[_file_payload()])
        return httpx.Response(404)

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        client = GitHubClient(client=async_client, token="", base_url="https://api.github.com")
        pull_request = await client.fetch_pull_request("https://github.com/openai/example/pull/123")
    finally:
        await async_client.aclose()

    assert pull_request.title == "Improve review pipeline"
    assert pull_request.author == "octocat"
    assert pull_request.files[0].filename == "src/app.py"
    assert all("authorization" not in request.headers for request in requests)


@pytest.mark.asyncio
async def test_fetch_pull_request_uses_token_when_configured() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/123"):
            return httpx.Response(200, json=_pr_payload())
        if request.url.path.endswith("/pulls/123/files"):
            return httpx.Response(200, json=[_file_payload()])
        return httpx.Response(404)

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        client = GitHubClient(client=async_client, token="ghp_test", base_url="https://api.github.com")
        await client.fetch_pull_request("https://github.com/openai/example/pull/123")
    finally:
        await async_client.aclose()

    assert requests[0].headers["authorization"] == "Bearer ghp_test"


@pytest.mark.asyncio
async def test_fetch_pull_request_handles_404() -> None:
    async_client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404)))
    try:
        client = GitHubClient(client=async_client, base_url="https://api.github.com")
        with pytest.raises(GitHubNotFoundError):
            await client.fetch_pull_request("https://github.com/openai/missing/pull/123")
    finally:
        await async_client.aclose()


@pytest.mark.asyncio
async def test_fetch_pull_request_handles_rate_limit() -> None:
    async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(403, headers={"x-ratelimit-remaining": "0"})
        )
    )
    try:
        client = GitHubClient(client=async_client, base_url="https://api.github.com")
        with pytest.raises(GitHubRateLimitError):
            await client.fetch_pull_request("https://github.com/openai/example/pull/123")
    finally:
        await async_client.aclose()


@pytest.mark.asyncio
async def test_fetch_pull_request_handles_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network unavailable", request=request)

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        client = GitHubClient(client=async_client, base_url="https://api.github.com")
        with pytest.raises(GitHubNetworkError):
            await client.fetch_pull_request("https://github.com/openai/example/pull/123")
    finally:
        await async_client.aclose()


@pytest.mark.asyncio
async def test_fetch_pull_request_rejects_too_many_files() -> None:
    async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=_pr_payload(changed_files=2)))
    )
    try:
        client = GitHubClient(client=async_client, base_url="https://api.github.com", max_files=1)
        with pytest.raises(GitHubLargePRError):
            await client.fetch_pull_request("https://github.com/openai/example/pull/123")
    finally:
        await async_client.aclose()


@pytest.mark.asyncio
async def test_fetch_pull_request_handles_missing_patch() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/pulls/123"):
            return httpx.Response(200, json=_pr_payload())
        if request.url.path.endswith("/pulls/123/files"):
            return httpx.Response(200, json=[_file_payload(patch=None)])
        return httpx.Response(404)

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        client = GitHubClient(client=async_client, base_url="https://api.github.com")
        pull_request = await client.fetch_pull_request("https://github.com/openai/example/pull/123")
    finally:
        await async_client.aclose()

    assert pull_request.files[0].patch is None


def test_normalizes_github_patch_to_parsed_diff_with_line_numbers() -> None:
    pull_request = _pull_request(
        [
            GitHubChangedFile(
                filename="src/app.py",
                status="modified",
                additions=1,
                deletions=0,
                changes=1,
                patch="""@@ -10,2 +10,3 @@ def run():
 value = load()
+print(value)
 return value""",
            )
        ]
    )

    parsed = normalize_github_pr_to_parsed_diff(pull_request)

    changed_file = parsed.files[0]
    assert changed_file.new_path == "src/app.py"
    assert changed_file.hunks[0].lines[1].new_line == 11
    assert changed_file.changed_line_ranges[0].start == 11


def test_normalized_lock_file_is_ignored_by_existing_preprocessor() -> None:
    pull_request = _pull_request(
        [
            GitHubChangedFile(
                filename="package-lock.json",
                status="modified",
                additions=1,
                deletions=1,
                changes=2,
                patch="""@@ -1 +1 @@
-{"lockfileVersion": 2}
+{"lockfileVersion": 3}""",
            )
        ]
    )

    prepared = prepare_review_chunks(normalize_github_pr_to_parsed_diff(pull_request))

    assert prepared.chunks == []
    assert prepared.skipped_files[0].reason == "generated or dependency file"


def test_normalized_missing_patch_file_has_no_reviewable_hunks() -> None:
    pull_request = _pull_request(
        [
            GitHubChangedFile(
                filename="src/app.py",
                status="modified",
                additions=10,
                deletions=0,
                changes=10,
                patch=None,
            )
        ]
    )

    prepared = prepare_review_chunks(normalize_github_pr_to_parsed_diff(pull_request))

    assert prepared.chunks == []
    assert prepared.skipped_files[0].reason == "no reviewable hunks"


def test_normalizes_multiple_changed_files() -> None:
    pull_request = _pull_request(
        [
            GitHubChangedFile(
                filename="src/app.py",
                status="modified",
                additions=1,
                deletions=0,
                changes=1,
                patch="""@@ -1 +1,2 @@
 value = 1
+next_value = 2""",
            ),
            GitHubChangedFile(
                filename="src/util.ts",
                status="added",
                additions=1,
                deletions=0,
                changes=1,
                patch="""@@ -0,0 +1 @@
+export const value = 1""",
            ),
        ]
    )

    parsed = normalize_github_pr_to_parsed_diff(pull_request)

    assert [file.new_path for file in parsed.files] == ["src/app.py", "src/util.ts"]


def _pr_payload(changed_files: int = 1) -> dict:
    return {
        "number": 123,
        "title": "Improve review pipeline",
        "state": "open",
        "user": {"login": "octocat"},
        "base": {"ref": "main"},
        "head": {"ref": "feature/review"},
        "additions": 4,
        "deletions": 1,
        "changed_files": changed_files,
    }


def _file_payload(patch: str | None = "@@ -1 +1,2 @@\n value = 1\n+next_value = 2") -> dict:
    payload = {
        "filename": "src/app.py",
        "status": "modified",
        "additions": 1,
        "deletions": 0,
        "changes": 1,
    }
    if patch is not None:
        payload["patch"] = patch
    return payload


def _pull_request(files: list[GitHubChangedFile]) -> GitHubPullRequest:
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
        additions=4,
        deletions=1,
        changed_files=len(files),
        files=files,
    )
