import pytest

from app.schemas.review import FindingCategory, FindingSource, ReviewFinding, Severity
from app.services.review_pipeline import ReviewPipeline


class FakeReviewer:
    async def review_chunk(self, chunk):
        return [
            ReviewFinding(
                file=chunk.file_path,
                line=chunk.start_line,
                category=FindingCategory.BUG,
                severity=Severity.HIGH,
                title="Possible null dereference",
                explanation="The AI reviewer identified a high-confidence runtime issue.",
                suggestion="Guard the value before dereferencing it.",
                confidence=0.91,
                source=FindingSource.AI,
            )
        ]


class RaisingReviewer:
    async def review_chunk(self, chunk):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_pipeline_combines_ai_and_deterministic_findings() -> None:
    raw_diff = """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,3 @@
 def run():
+    print("debug")
+    return None.value
"""
    pipeline = ReviewPipeline(ai_reviewer=FakeReviewer())

    response = await pipeline.review_diff(raw_diff)

    assert response.risk_level == "high"
    assert response.stats.files_reviewed == 1
    assert response.stats.high_severity == 1
    assert response.stats.low_severity == 1
    assert [finding.severity for finding in response.findings] == [Severity.HIGH, Severity.LOW]


@pytest.mark.asyncio
async def test_pipeline_continues_when_ai_reviewer_fails() -> None:
    raw_diff = """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
 def run():
+    print("debug")
"""
    pipeline = ReviewPipeline(ai_reviewer=RaisingReviewer())

    response = await pipeline.review_diff(raw_diff)

    assert response.risk_level == "low"
    assert response.stats.findings == 1
    assert response.findings[0].source == FindingSource.DETERMINISTIC


@pytest.mark.asyncio
async def test_pipeline_returns_low_risk_when_only_ignored_files_change() -> None:
    raw_diff = """diff --git a/yarn.lock b/yarn.lock
index 1111111..2222222 100644
--- a/yarn.lock
+++ b/yarn.lock
@@ -1 +1 @@
-left
+right
"""
    pipeline = ReviewPipeline(ai_reviewer=FakeReviewer())

    response = await pipeline.review_diff(raw_diff)

    assert response.risk_level == "low"
    assert response.stats.files_reviewed == 0
    assert response.stats.findings == 0
    assert "No reviewable source changes" in response.summary
