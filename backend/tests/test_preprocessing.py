from app.schemas.preprocessing import PreprocessingConfig
from app.services.diff_parser import parse_unified_diff
from app.services.preprocessing import prepare_review_chunks


def test_filters_lock_files() -> None:
    parsed = parse_unified_diff(
        """diff --git a/package-lock.json b/package-lock.json
index 1111111..2222222 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1 +1 @@
-{"lockfileVersion": 2}
+{"lockfileVersion": 3}
"""
    )

    prepared = prepare_review_chunks(parsed)

    assert prepared.chunks == []
    assert prepared.skipped_files[0].reason == "generated or dependency file"


def test_keeps_normal_source_files_and_line_numbers() -> None:
    parsed = parse_unified_diff(
        """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -10,2 +10,3 @@ def run():
 value = load()
+print(value)
 return value
"""
    )

    prepared = prepare_review_chunks(parsed)

    assert prepared.files_reviewed == 1
    chunk = prepared.chunks[0]
    assert chunk.file_path == "src/app.py"
    assert chunk.start_line == 11
    assert chunk.end_line == 11
    assert chunk.hunks[0].lines[1].new_line == 11
    assert "11: +print(value)" in chunk.diff_text


def test_handles_multiple_files() -> None:
    parsed = parse_unified_diff(
        """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
 value = 1
+next_value = 2
diff --git a/src/util.ts b/src/util.ts
index 1111111..2222222 100644
--- a/src/util.ts
+++ b/src/util.ts
@@ -1 +1,2 @@
 export const value = 1
+export const nextValue = 2
"""
    )

    prepared = prepare_review_chunks(parsed)

    assert prepared.files_reviewed == 2
    assert prepared.is_large_diff is False
    assert [chunk.file_path for chunk in prepared.chunks] == ["src/app.py", "src/util.ts"]


def test_splits_large_hunks_and_marks_large_diff() -> None:
    added_lines = "\n".join(f"+line_{index} = {index}" for index in range(1, 8))
    parsed = parse_unified_diff(
        f"""diff --git a/src/generated_case.py b/src/generated_case.py
index 1111111..2222222 100644
--- a/src/generated_case.py
+++ b/src/generated_case.py
@@ -0,0 +1,7 @@
{added_lines}
"""
    )

    prepared = prepare_review_chunks(
        parsed,
        PreprocessingConfig(max_diff_lines_per_chunk=3, max_chunk_chars=10_000, large_diff_bytes=20),
    )

    assert prepared.is_large_diff is True
    assert len(prepared.chunks) == 3
    assert [(chunk.start_line, chunk.end_line) for chunk in prepared.chunks] == [(1, 3), (4, 6), (7, 7)]
    assert prepared.chunks[1].hunks[0].lines[0].new_line == 4


def test_skips_binary_files() -> None:
    parsed = parse_unified_diff(
        """diff --git a/assets/logo.png b/assets/logo.png
new file mode 100644
index 0000000..1111111
Binary files /dev/null and b/assets/logo.png differ
"""
    )

    prepared = prepare_review_chunks(parsed)

    assert prepared.chunks == []
    assert prepared.skipped_files[0].reason == "binary file"
