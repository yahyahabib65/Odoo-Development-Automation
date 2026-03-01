"""Odoo log parsing for install and test results.

Parses stdout/stderr from Odoo CLI commands to extract:
- Install success/failure from module installation
- Per-test pass/fail results from test execution
- Traceback text for error diagnosis
"""

from __future__ import annotations

import re

from odoo_gen_utils.validation.types import TestResult

# --- Compiled regex patterns ---

# Odoo log line with ERROR or CRITICAL severity
_ERROR_LINE = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s[\d:,]+\s+\d+\s+(ERROR|CRITICAL)\s+\S+\s+(.+)$",
    re.MULTILINE,
)

# Module not found pattern - handles both quoted and unquoted module names
_MODULE_NOT_FOUND = re.compile(
    r"No module named ['\"]([^'\"]+)['\"]|No module named (\S+)",
    re.MULTILINE,
)

# Successful module loading indicator
_MODULES_LOADED = re.compile(
    r"modules loaded",
    re.IGNORECASE,
)

# Test pass pattern: "test_name ... ok"
_TEST_PASS = re.compile(
    r"(\S+\.tests\.\S+):\s+(test_\S+)\s+\.\.\.\s+ok",
    re.MULTILINE,
)

# Test failure pattern: FAIL or ERROR followed by test info
_TEST_FAIL = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s[\d:,]+\s+\d+\s+(FAIL|ERROR)\s+\S+\s+\S+\.tests\.\S+:\s+(test_\S+)",
    re.MULTILINE,
)

# Test summary pattern
_TEST_SUMMARY = re.compile(
    r"Ran\s+(\d+)\s+tests?\s+in\s+([\d.]+)s",
    re.MULTILINE,
)

# Traceback start
_TRACEBACK_START = re.compile(r"^Traceback \(most recent call last\):", re.MULTILINE)


def parse_install_log(log_text: str) -> tuple[bool, str]:
    """Parse Odoo stdout/stderr from module install.

    Returns:
        Tuple of (success, error_message).
        success is True if modules loaded without ERROR/CRITICAL.
        error_message contains the relevant error detail on failure.
    """
    if not log_text or not log_text.strip():
        return (False, "No log output")

    # Check for "No module named" first (specific error)
    module_not_found = _MODULE_NOT_FOUND.search(log_text)
    if module_not_found:
        # group(1) is quoted name, group(2) is unquoted name
        module_name = module_not_found.group(1) or module_not_found.group(2)
        return (False, f"Module not found: {module_name}")

    # Check for ERROR or CRITICAL log lines
    error_matches = _ERROR_LINE.findall(log_text)
    if error_matches:
        # Extract the most relevant error message
        # error_matches is list of (severity, message) tuples
        error_messages = [msg.strip() for _severity, msg in error_matches]
        # Return the first error as the primary message
        return (False, error_messages[0])

    # Check for traceback without Odoo-formatted ERROR lines
    if "Traceback" in log_text:
        tb = extract_traceback(log_text)
        # Extract the last line of the traceback (the exception)
        tb_lines = tb.strip().splitlines()
        if tb_lines:
            return (False, tb_lines[-1].strip())
        return (False, "Traceback detected in log output")

    # Check for successful module loading
    if _MODULES_LOADED.search(log_text):
        return (True, "")

    # No clear success or failure indicators
    return (False, "Unable to determine install result from log output")


def parse_test_log(log_text: str) -> tuple[TestResult, ...]:
    """Parse Odoo test output to extract per-test pass/fail results.

    Returns:
        Tuple of TestResult dataclasses, one per test found.
    """
    if not log_text or not log_text.strip():
        return ()

    results: list[TestResult] = []
    seen_tests: set[str] = set()

    # Find all passing tests
    for match in _TEST_PASS.finditer(log_text):
        test_name = match.group(2)
        if test_name not in seen_tests:
            seen_tests.add(test_name)
            results.append(TestResult(test_name=test_name, passed=True))

    # Find all failing tests
    for match in _TEST_FAIL.finditer(log_text):
        test_name = match.group(2)
        failure_type = match.group(1)  # FAIL or ERROR
        if test_name not in seen_tests:
            seen_tests.add(test_name)
            # Try to extract error message from following lines
            error_msg = _extract_failure_message(log_text, match.end())
            results.append(
                TestResult(
                    test_name=test_name,
                    passed=False,
                    error_message=error_msg or f"{failure_type}: {test_name}",
                )
            )

    # Parse test summary for duration info
    summary_match = _TEST_SUMMARY.search(log_text)
    if summary_match and results:
        total_duration = float(summary_match.group(2))
        avg_duration = total_duration / len(results) if results else 0.0
        # Update results with averaged duration (frozen dataclass, create new)
        results = [
            TestResult(
                test_name=r.test_name,
                passed=r.passed,
                error_message=r.error_message,
                duration_seconds=avg_duration,
            )
            for r in results
        ]

    return tuple(results)


def _extract_failure_message(log_text: str, start_pos: int) -> str:
    """Extract error message following a FAIL/ERROR test line.

    Looks for the next non-log-formatted line after the failure marker.
    """
    remaining = log_text[start_pos:].strip()
    lines = remaining.splitlines()
    for line in lines[:3]:  # Check next 3 lines max
        stripped = line.strip()
        if stripped and not re.match(r"^\d{4}-\d{2}-\d{2}", stripped):
            return stripped
    return ""


def extract_traceback(log_text: str) -> str:
    """Extract Python traceback from log for diagnosis.

    Finds 'Traceback (most recent call last):' and captures until
    the exception line (next line that starts at column 0 and is not
    indented, after at least one indented line).

    Returns:
        The traceback text, or empty string if not found.
    """
    if not log_text:
        return ""

    match = _TRACEBACK_START.search(log_text)
    if not match:
        return ""

    # Start from the traceback line
    start = match.start()
    lines = log_text[start:].splitlines()

    if not lines:
        return ""

    tb_lines: list[str] = [lines[0]]  # "Traceback (most recent call last):"
    found_indented = False

    for line in lines[1:]:
        if line.startswith("  ") or line.startswith("\t"):
            found_indented = True
            tb_lines.append(line)
        elif found_indented:
            # This is the exception line (e.g., "KeyError: 'missing_field'")
            tb_lines.append(line)
            break
        else:
            # Unexpected format, include it and keep looking
            tb_lines.append(line)
            if not line.strip():
                continue
            # Non-indented, non-empty line before any indented line
            # This might be a continuation or malformed traceback
            break

    return "\n".join(tb_lines)
