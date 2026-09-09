from types import SimpleNamespace

import pytest

from app.schemas.review import AIReviewOutput, FindingCategory, FindingSource, ReviewFinding, Severity
from app.services.ai_reviewer import OpenAIReviewer
from app.services.diff_parser import parse_unified_diff
from app.services.preprocessing import prepare_review_chunks


def _chunk():
    parsed = parse_unified_diff(
        """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
 def run():
+    return None.value
"""
    )
    return prepare_review_chunks(parsed).chunks[0]


class FakeResponses:
    def __init__(self, output):
        self.output = output
        self.call_kwargs = None

    async def parse(self, **kwargs):
        self.call_kwargs = kwargs
        return self.output


class FakeClient:
    def __init__(self, output):
        self.responses = FakeResponses(output)


@pytest.mark.asyncio
async def test_openai_reviewer_parses_structured_findings() -> None:
    chunk = _chunk()
    output = SimpleNamespace(
        output_parsed=AIReviewOutput(
            findings=[
                ReviewFinding(
                    file="src/app.py",
                    line=2,
                    category=FindingCategory.BUG,
                    severity=Severity.HIGH,
                    title="None dereference",
                    explanation="The changed code dereferences None directly.",
                    suggestion="Return a real object or guard before reading the attribute.",
                    confidence=0.95,
                )
            ]
        )
    )
    client = FakeClient(output)
    reviewer = OpenAIReviewer(client=client, api_key="test", model="test-model")

    findings = await reviewer.review_chunk(chunk)

    assert len(findings) == 1
    assert findings[0].source == FindingSource.AI
    assert client.responses.call_kwargs["text_format"] is AIReviewOutput
    assert "src/app.py" in client.responses.call_kwargs["input"]


@pytest.mark.asyncio
async def test_openai_reviewer_filters_findings_for_other_files() -> None:
    chunk = _chunk()
    output = SimpleNamespace(
        output_parsed=AIReviewOutput(
            findings=[
                ReviewFinding(
                    file="src/other.py",
                    line=2,
                    category=FindingCategory.BUG,
                    severity=Severity.HIGH,
                    title="Wrong file",
                    explanation="This finding points at a file outside the current review chunk.",
                    suggestion="Only return findings for the provided file.",
                    confidence=0.8,
                )
            ]
        )
    )
    reviewer = OpenAIReviewer(client=FakeClient(output), api_key="test")

    assert await reviewer.review_chunk(chunk) == []


@pytest.mark.asyncio
async def test_openai_reviewer_handles_missing_api_key() -> None:
    reviewer = OpenAIReviewer(client=None, api_key="")

    assert await reviewer.review_chunk(_chunk()) == []


@pytest.mark.asyncio
async def test_openai_reviewer_handles_invalid_model_output() -> None:
    reviewer = OpenAIReviewer(client=FakeClient(SimpleNamespace(output_parsed={"findings": [{"file": "src/app.py"}]})), api_key="test")

    assert await reviewer.review_chunk(_chunk()) == []


@pytest.mark.asyncio
async def test_openai_reviewer_handles_api_errors() -> None:
    class ErrorResponses:
        async def parse(self, **kwargs):
            raise TimeoutError("request timed out")

    class ErrorClient:
        responses = ErrorResponses()

    reviewer = OpenAIReviewer(client=ErrorClient(), api_key="test")

    assert await reviewer.review_chunk(_chunk()) == []
