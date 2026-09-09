from __future__ import annotations

import logging
from typing import Protocol

from openai import AsyncOpenAI
from app.core.config import get_settings
from app.schemas.preprocessing import ReviewChunk
from app.schemas.review import AIReviewOutput, FindingSource, ReviewFinding


logger = logging.getLogger(__name__)


class ChunkReviewer(Protocol):
    async def review_chunk(self, chunk: ReviewChunk) -> list[ReviewFinding]:
        ...


class OpenAIReviewer:
    def __init__(
        self,
        client: AsyncOpenAI | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        settings = get_settings()
        configured_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        self.api_key = api_key if api_key is not None else configured_key
        self.model = model or settings.openai_model
        self.timeout_seconds = timeout_seconds or settings.openai_timeout_seconds
        self.max_output_tokens = max_output_tokens or settings.openai_max_output_tokens
        self._client = client

    async def review_chunk(self, chunk: ReviewChunk) -> list[ReviewFinding]:
        if self._client is None and not self.api_key:
            logger.info("Skipping AI review because OPENAI_API_KEY is not configured")
            return []

        client = self._client or AsyncOpenAI(api_key=self.api_key, timeout=self.timeout_seconds)

        try:
            response = await client.responses.parse(
                model=self.model,
                instructions=_SYSTEM_PROMPT,
                input=_build_user_prompt(chunk),
                text_format=AIReviewOutput,
                max_output_tokens=self.max_output_tokens,
                timeout=self.timeout_seconds,
            )
            output = _extract_ai_output(response)
        except Exception as exc:
            logger.warning("AI review failed for chunk %s with %s", chunk.chunk_id, exc.__class__.__name__)
            return []

        return _sanitize_findings(output.findings, chunk)


def _extract_ai_output(response: object) -> AIReviewOutput:
    parsed = getattr(response, "output_parsed", None)
    if isinstance(parsed, AIReviewOutput):
        return parsed
    if isinstance(parsed, dict):
        return AIReviewOutput.model_validate(parsed)
    if parsed is None:
        return AIReviewOutput()
    return AIReviewOutput.model_validate(parsed)


def _sanitize_findings(findings: list[ReviewFinding], chunk: ReviewChunk) -> list[ReviewFinding]:
    sanitized: list[ReviewFinding] = []
    for finding in findings:
        if finding.file != chunk.file_path:
            continue
        sanitized.append(finding.model_copy(update={"source": FindingSource.AI}))
    return sanitized


def _build_user_prompt(chunk: ReviewChunk) -> str:
    line_ranges = ", ".join(
        f"{line_range.start}-{line_range.end}" if line_range.start != line_range.end else str(line_range.start)
        for line_range in chunk.changed_line_ranges
    )
    line_ranges = line_ranges or "no added-line range; review removed/context lines only if materially relevant"

    return f"""Review this prepared diff chunk.

File: {chunk.file_path}
Old path: {chunk.old_path or chunk.file_path}
Status: {chunk.status}
Language: {chunk.language or "unknown"}
Changed new-file line ranges: {line_ranges}
Additions: {chunk.additions}
Deletions: {chunk.deletions}

Only review changed code in this chunk unless surrounding context materially affects correctness.
Do not review generated or ignored files.

{chunk.diff_text}
"""


_SYSTEM_PROMPT = """You are a senior software engineer performing a focused pull request review.

Return structured findings only. Review changed code, not unrelated architecture. Focus on likely bugs, edge cases, security, performance, maintainability, and missing or weak tests. Avoid cosmetic nitpicks and do not invent bugs. Prefer actionable findings. Every finding must reference the provided file and the changed/new line number where possible. Use severity low, medium, or high. Confidence must be between 0 and 1. Avoid duplicates. Distinguish plausible concerns from high-confidence defects. Do not complain about missing context unless the missing context genuinely prevents a conclusion. Do not suggest changes unrelated to the diff.
"""
