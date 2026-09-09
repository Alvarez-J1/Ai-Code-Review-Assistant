import pytest

from app.schemas.diff import DiffLineKind, FileChangeStatus
from app.services.diff_parser import DiffParseError, parse_unified_diff


def test_parse_modified_file_with_hunk_metadata_and_line_ranges() -> None:
    raw_diff = """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,4 +1,5 @@ def hello():
 import os
-print("old")
+print("new")
+TODO = "later"
 return 1
"""

    parsed = parse_unified_diff(raw_diff)

    assert parsed.raw_size_bytes == len(raw_diff.encode("utf-8"))
    assert parsed.total_additions == 2
    assert parsed.total_deletions == 1
    assert len(parsed.files) == 1

    changed_file = parsed.files[0]
    assert changed_file.old_path == "src/app.py"
    assert changed_file.new_path == "src/app.py"
    assert changed_file.status == FileChangeStatus.MODIFIED
    assert changed_file.extension == ".py"
    assert changed_file.language == "Python"
    assert changed_file.additions == 2
    assert changed_file.deletions == 1
    assert [(line_range.start, line_range.end) for line_range in changed_file.changed_line_ranges] == [(2, 3)]

    hunk = changed_file.hunks[0]
    assert hunk.old_start == 1
    assert hunk.old_count == 4
    assert hunk.new_start == 1
    assert hunk.new_count == 5
    assert hunk.section_header == "def hello():"
    assert [line.kind for line in hunk.lines] == [
        DiffLineKind.CONTEXT,
        DiffLineKind.REMOVED,
        DiffLineKind.ADDED,
        DiffLineKind.ADDED,
        DiffLineKind.CONTEXT,
    ]
    assert hunk.lines[2].new_line == 2
    assert hunk.lines[1].old_line == 2


def test_parse_added_file() -> None:
    raw_diff = """diff --git a/src/new_module.py b/src/new_module.py
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/src/new_module.py
@@ -0,0 +1,2 @@
+def feature():
+    return True
"""

    parsed = parse_unified_diff(raw_diff)

    changed_file = parsed.files[0]
    assert changed_file.status == FileChangeStatus.ADDED
    assert changed_file.old_path is None
    assert changed_file.new_path == "src/new_module.py"
    assert changed_file.additions == 2
    assert changed_file.deletions == 0
    assert [(line_range.start, line_range.end) for line_range in changed_file.changed_line_ranges] == [(1, 2)]


def test_parse_deleted_file() -> None:
    raw_diff = """diff --git a/src/old_module.py b/src/old_module.py
deleted file mode 100644
index 1111111..0000000
--- a/src/old_module.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def old_feature():
-    return True
"""

    parsed = parse_unified_diff(raw_diff)

    changed_file = parsed.files[0]
    assert changed_file.status == FileChangeStatus.DELETED
    assert changed_file.old_path == "src/old_module.py"
    assert changed_file.new_path is None
    assert changed_file.additions == 0
    assert changed_file.deletions == 2
    assert changed_file.changed_line_ranges == []


def test_parse_renamed_file() -> None:
    raw_diff = """diff --git a/src/old_name.py b/src/new_name.py
similarity index 86%
rename from src/old_name.py
rename to src/new_name.py
index 1111111..2222222 100644
--- a/src/old_name.py
+++ b/src/new_name.py
@@ -1 +1 @@
-VALUE = "old"
+VALUE = "new"
"""

    parsed = parse_unified_diff(raw_diff)

    changed_file = parsed.files[0]
    assert changed_file.status == FileChangeStatus.RENAMED
    assert changed_file.old_path == "src/old_name.py"
    assert changed_file.new_path == "src/new_name.py"
    assert changed_file.additions == 1
    assert changed_file.deletions == 1


def test_parse_binary_file_marks_file_without_hunks() -> None:
    raw_diff = """diff --git a/assets/logo.png b/assets/logo.png
new file mode 100644
index 0000000..1111111
Binary files /dev/null and b/assets/logo.png differ
"""

    parsed = parse_unified_diff(raw_diff)

    changed_file = parsed.files[0]
    assert changed_file.status == FileChangeStatus.ADDED
    assert changed_file.is_binary is True
    assert changed_file.new_path == "assets/logo.png"
    assert changed_file.hunks == []


def test_lock_files_are_marked_generated() -> None:
    raw_diff = """diff --git a/package-lock.json b/package-lock.json
index 1111111..2222222 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1 +1 @@
-{"lockfileVersion": 2}
+{"lockfileVersion": 3}
"""

    parsed = parse_unified_diff(raw_diff)

    assert parsed.files[0].is_generated is True


def test_empty_diff_is_rejected() -> None:
    with pytest.raises(DiffParseError, match="empty"):
        parse_unified_diff("   ")
