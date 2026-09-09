from __future__ import annotations

import shlex
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.schemas.diff import ParsedDiff
from app.schemas.github import GitHubChangedFile, GitHubPullRequest, GitHubPRReference
from app.services.diff_parser import parse_unified_diff


class GitHubError(RuntimeError):
    status_code = 502
    public_message = "GitHub request failed"


class InvalidGitHubPRError(ValueError):
    pass


class GitHubNotFoundError(GitHubError):
    status_code = 404
    public_message = "GitHub pull request was not found"


class GitHubRateLimitError(GitHubError):
    status_code = 429
    public_message = "GitHub rate limit exceeded"


class GitHubNetworkError(GitHubError):
    status_code = 502
    public_message = "Unable to reach GitHub"


class GitHubTimeoutError(GitHubNetworkError):
    status_code = 504
    public_message = "GitHub request timed out"


class GitHubLargePRError(GitHubError):
    status_code = 413
    public_message = "GitHub pull request is too large to review in this mode"


class GitHubAPIError(GitHubError):
    pass


def parse_github_pr_url(url: str) -> GitHubPRReference:
    parsed = urlparse(url.strip())

    if parsed.scheme not in {"http", "https"}:
        raise InvalidGitHubPRError("GitHub PR URL must use http or https")

    if parsed.netloc.lower() != "github.com":
        raise InvalidGitHubPRError("URL must point to github.com")

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) != 4 or path_parts[2] != "pull":
        raise InvalidGitHubPRError("URL must have the form https://github.com/{owner}/{repo}/pull/{number}")

    owner, repo, _, pr_number_raw = path_parts
    if not pr_number_raw.isdigit() or int(pr_number_raw) < 1:
        raise InvalidGitHubPRError("GitHub pull request number must be a positive integer")

    pr_number = int(pr_number_raw)
    return GitHubPRReference(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        html_url=f"https://github.com/{owner}/{repo}/pull/{pr_number}",
    )


class GitHubClient:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        token: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        timeout_seconds: float | None = None,
        max_files: int | None = None,
    ) -> None:
        settings = get_settings()
        configured_token = settings.github_token.get_secret_value() if settings.github_token else None
        self.token = token if token is not None else configured_token
        self.base_url = (base_url or settings.github_api_base_url).rstrip("/")
        self.api_version = api_version or settings.github_api_version
        self.timeout_seconds = timeout_seconds or settings.github_timeout_seconds
        self.max_files = max_files or settings.github_max_files
        self._client = client

    async def fetch_pull_request(self, url: str) -> GitHubPullRequest:
        reference = parse_github_pr_url(url)
        async with self._client_context() as client:
            pr_payload = await self._get_json(
                client,
                f"/repos/{reference.owner}/{reference.repo}/pulls/{reference.pr_number}",
            )
            if not isinstance(pr_payload, dict):
                raise GitHubAPIError()

            changed_files = pr_payload.get("changed_files")
            if isinstance(changed_files, int) and changed_files > self.max_files:
                raise GitHubLargePRError()

            files_payload = await self._fetch_files(client, reference)

        return GitHubPullRequest(
            reference=reference,
            title=pr_payload.get("title"),
            state=pr_payload.get("state"),
            author=(pr_payload.get("user") or {}).get("login"),
            base_ref=(pr_payload.get("base") or {}).get("ref"),
            head_ref=(pr_payload.get("head") or {}).get("ref"),
            additions=pr_payload.get("additions"),
            deletions=pr_payload.get("deletions"),
            changed_files=changed_files,
            files=[
                GitHubChangedFile(
                    filename=file_payload["filename"],
                    status=file_payload.get("status", "modified"),
                    additions=file_payload.get("additions", 0),
                    deletions=file_payload.get("deletions", 0),
                    changes=file_payload.get("changes", 0),
                    patch=file_payload.get("patch"),
                    previous_filename=file_payload.get("previous_filename"),
                )
                for file_payload in files_payload
            ],
        )

    async def _fetch_files(
        self,
        client: httpx.AsyncClient,
        reference: GitHubPRReference,
    ) -> list[dict]:
        files: list[dict] = []
        per_page = 100
        max_pages = (self.max_files // per_page) + 2

        for page in range(1, max_pages + 1):
            page_payload = await self._get_json(
                client,
                f"/repos/{reference.owner}/{reference.repo}/pulls/{reference.pr_number}/files",
                params={"per_page": per_page, "page": page},
            )
            if not isinstance(page_payload, list):
                raise GitHubAPIError()

            files.extend(page_payload)
            if len(files) > self.max_files:
                raise GitHubLargePRError()
            if len(page_payload) < per_page:
                return files

        raise GitHubLargePRError()

    async def _get_json(self, client: httpx.AsyncClient, path: str, params: dict | None = None) -> object:
        try:
            response = await client.get(
                f"{self.base_url}{path}",
                params=params,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise GitHubTimeoutError() from exc
        except httpx.RequestError as exc:
            raise GitHubNetworkError() from exc

        if response.status_code == 404:
            raise GitHubNotFoundError()
        if response.status_code == 429 or (
            response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"
        ):
            raise GitHubRateLimitError()
        if response.status_code >= 400:
            raise GitHubAPIError()

        try:
            return response.json()
        except ValueError as exc:
            raise GitHubAPIError() from exc

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.api_version,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _client_context(self) -> _ClientContext:
        return _ClientContext(self._client, self.timeout_seconds)


class _ClientContext:
    def __init__(self, client: httpx.AsyncClient | None, timeout_seconds: float) -> None:
        self.client = client
        self.timeout_seconds = timeout_seconds
        self.created_client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> httpx.AsyncClient:
        if self.client is not None:
            return self.client
        self.created_client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self.created_client

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if self.created_client is not None:
            await self.created_client.aclose()


def normalize_github_pr_to_parsed_diff(pull_request: GitHubPullRequest) -> ParsedDiff:
    raw_diff = "\n".join(_changed_file_to_diff(changed_file) for changed_file in pull_request.files)
    if not raw_diff.strip():
        return ParsedDiff(files=[], raw_size_bytes=0)
    return parse_unified_diff(raw_diff)


def _changed_file_to_diff(changed_file: GitHubChangedFile) -> str:
    old_path = changed_file.previous_filename if changed_file.status == "renamed" else changed_file.filename
    new_path = changed_file.filename

    if changed_file.status == "added":
        old_marker = "/dev/null"
        new_marker = f"b/{new_path}"
    elif changed_file.status == "removed":
        old_marker = f"a/{old_path}"
        new_marker = "/dev/null"
    else:
        old_marker = f"a/{old_path}"
        new_marker = f"b/{new_path}"

    lines = [f"diff --git {_quote_git_path('a', old_path)} {_quote_git_path('b', new_path)}"]
    if changed_file.status == "added":
        lines.append("new file mode 100644")
    elif changed_file.status == "removed":
        lines.append("deleted file mode 100644")
    elif changed_file.status == "renamed" and changed_file.previous_filename:
        lines.append(f"rename from {changed_file.previous_filename}")
        lines.append(f"rename to {changed_file.filename}")

    lines.append(f"--- {old_marker}")
    lines.append(f"+++ {new_marker}")
    if changed_file.patch:
        lines.append(changed_file.patch.rstrip("\n"))
    return "\n".join(lines)


def _quote_git_path(prefix: str, path: str) -> str:
    return shlex.quote(f"{prefix}/{path}")
