"""Tests for rules/validate.py PEP 723 metadata and python.rules content."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.manual

RULES_DIR = Path(__file__).resolve().parents[1]
VALIDATE = RULES_DIR / "validate.py"


def pep723_block(source: str) -> str | None:
    match = re.search(r"# /// script\n(.*?)# ///\n", source, re.DOTALL)
    return match.group(1) if match else None


class TestPep723Metadata:
    """rules/validate.py must carry its own dependency (textX) inline."""

    def test_block_present(self):
        assert pep723_block(
            VALIDATE.read_text(encoding="utf-8")
        ), "PEP 723 script block missing"

    def test_textx_pinned(self):
        block = pep723_block(VALIDATE.read_text(encoding="utf-8"))
        assert block and "textx==4.4.0" in block

    def test_requires_python(self):
        block = pep723_block(VALIDATE.read_text(encoding="utf-8"))
        assert block and 'requires-python = ">=3.13"' in block

    def test_docstring_mentions_uv_run(self):
        header = VALIDATE.read_text(encoding="utf-8")[:400]
        assert "uv run" in header


class TestUvRun:
    """uv run executes the standalone validator without the project venv."""

    def test_validate_ok(self):
        completed = subprocess.run(
            [
                "uv",
                "run",
                "--no-project",
                str(VALIDATE),
                str(RULES_DIR / "python.rules"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert "OK" in completed.stdout


class TestPythonRules:
    """python.rules must contain the StrEnum-over-literals policy."""

    def test_strenum_rule_present(self):
        rules = (RULES_DIR / "python.rules").read_text(encoding="utf-8")
        assert re.search(
            r"^\[types\]\s*$", rules, re.MULTILINE
        ), "scope [types] missing"
        assert re.search(
            r"^PREFER enum\.StrEnum_with_auto OVER bare_string_literals"
            r" WHEN string_values_compared_or_matched\s*$",
            rules,
            re.MULTILINE,
        ), "StrEnum policy line missing"

    def test_documentation_rule_present(self):
        rules = (RULES_DIR / "python.rules").read_text(encoding="utf-8")
        assert re.search(r"^\[documentation\]\s*$", rules, re.MULTILINE)
        assert re.search(
            r"^AVOID docstrings"
            r" WHEN purpose_evident_from_name_and_parameters\s*$",
            rules,
            re.MULTILINE,
        )
