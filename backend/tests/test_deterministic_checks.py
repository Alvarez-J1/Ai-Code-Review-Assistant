from app.schemas.preprocessing import PreprocessingConfig
from app.schemas.review import FindingCategory, FindingSource
from app.services.deterministic_checks import run_deterministic_checks
from app.services.diff_parser import parse_unified_diff
from app.services.preprocessing import prepare_review_chunks


def _chunks(raw_diff: str):
    return prepare_review_chunks(parse_unified_diff(raw_diff)).chunks


def test_detects_console_log_and_ignores_comment() -> None:
    chunks = _chunks(
        """diff --git a/src/app.ts b/src/app.ts
index 1111111..2222222 100644
--- a/src/app.ts
+++ b/src/app.ts
@@ -1 +1,3 @@
 export function run() {
+  console.log("debug")
+  // console.log("documented")
 }
"""
    )

    findings = run_deterministic_checks(chunks)

    assert len([finding for finding in findings if finding.title == "Debug console output committed"]) == 1
    assert findings[0].source == FindingSource.DETERMINISTIC


def test_detects_python_print() -> None:
    chunks = _chunks(
        """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
 def run():
+    print("debug")
"""
    )

    findings = run_deterministic_checks(chunks)

    assert any(finding.title == "Debug print statement committed" for finding in findings)


def test_detects_todo_or_fixme() -> None:
    chunks = _chunks(
        """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
 def run():
+    # TODO: handle retries
"""
    )

    findings = run_deterministic_checks(chunks)

    assert any(finding.category == FindingCategory.READABILITY and "TODO" in finding.title for finding in findings)


def test_todo_string_literal_is_not_treated_as_comment() -> None:
    chunks = _chunks(
        """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
 def run():
+    label = "TODO"
"""
    )

    findings = run_deterministic_checks(chunks)

    assert not any("TODO" in finding.title for finding in findings)


def test_detects_bare_except_and_empty_handler() -> None:
    chunks = _chunks(
        """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,5 @@
 def run():
+    try:
+        risky()
+    except:
+        pass
"""
    )

    findings = run_deterministic_checks(chunks)

    assert any(finding.title == "Bare except catches too much" for finding in findings)
    assert any(finding.title == "Empty exception handler" for finding in findings)


def test_detects_hardcoded_secrets_and_avoids_env_reads() -> None:
    chunks = _chunks(
        """diff --git a/src/settings.py b/src/settings.py
index 1111111..2222222 100644
--- a/src/settings.py
+++ b/src/settings.py
@@ -1 +1,3 @@
 import os
+API_KEY = "sk_test_1234567890abcdef"
+TOKEN = os.getenv("TOKEN")
"""
    )

    findings = run_deterministic_checks(chunks)

    assert len([finding for finding in findings if finding.title == "Potential hard-coded secret"]) == 1


def test_detects_large_added_python_function() -> None:
    body = "\n".join(f"+    value_{index} = {index}" for index in range(90))
    chunks = _chunks(
        f"""diff --git a/src/big.py b/src/big.py
index 1111111..2222222 100644
--- a/src/big.py
+++ b/src/big.py
@@ -0,0 +1,91 @@
+def build():
{body}
"""
    )

    findings = run_deterministic_checks(chunks)

    assert any(finding.title == "Large newly added function" for finding in findings)


def test_detects_missing_tests_for_significant_source_change() -> None:
    body = "\n".join(f"+    value_{index} = {index}" for index in range(6))
    chunks = _chunks(
        f"""diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -0,0 +1,7 @@
+def run():
{body}
"""
    )

    findings = run_deterministic_checks(chunks, PreprocessingConfig(significant_source_change_lines=5))

    assert any(finding.title == "Significant source change without tests" for finding in findings)


def test_missing_tests_check_is_skipped_when_tests_change() -> None:
    chunks = _chunks(
        """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -0,0 +1,5 @@
+def run():
+    return 1
+def other():
+    return 2
+VALUE = 3
diff --git a/tests/test_app.py b/tests/test_app.py
index 1111111..2222222 100644
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1 +1,2 @@
 def test_run():
+    assert True
"""
    )

    findings = run_deterministic_checks(chunks, PreprocessingConfig(significant_source_change_lines=3))

    assert not any(finding.title == "Significant source change without tests" for finding in findings)
