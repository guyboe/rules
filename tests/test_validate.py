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
        assert pep723_block(VALIDATE.read_text(encoding="utf-8")), (
            "PEP 723 script block missing"
        )

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
                str(RULES_DIR / "python.glossary"),
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
        assert re.search(r"^\[types\]\s*$", rules, re.MULTILINE), (
            "scope [types] missing"
        )
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


def validate(store: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            str(VALIDATE),
            str(store / "python.rules"),
            str(store / "python.glossary"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


class TestGlossaryFile:
    """python.glossary carries the per-symbol explanations."""

    def test_marker_present(self):
        rules = (RULES_DIR / "python.rules").read_text(encoding="utf-8")
        assert "GLOSSARY" not in rules
        assert (RULES_DIR / "python.glossary").is_file()

    def test_entries_present(self):
        glossary = (RULES_DIR / "python.glossary").read_text(encoding="utf-8")
        assert re.search(r"^simple_design — \S", glossary, re.MULTILINE)
        assert re.search(
            r"^purpose_evident_from_name_and_parameters — \S",
            glossary,
            re.MULTILINE,
        )

    def test_entries_alphabetical(self):
        glossary = (RULES_DIR / "python.glossary").read_text(encoding="utf-8")
        names = [
            line.split(" — ")[0]
            for line in glossary.splitlines()
            if " — " in line and not line.startswith("#")
        ]
        assert names == sorted(names)


class TestGlossaryValidation:
    """The validator enforces the glossary/policy contract and the order."""

    def test_unknown_entry_rejected(self, store):
        glossary = store / "python.glossary"
        glossary.write_text(
            "zzz_suffix — unused\n",  # alphabetically last, keeps order valid
            encoding="utf-8",
        )
        completed = validate(store)
        assert completed.returncode == 1
        assert "not used by any policy" in completed.stderr

    def test_missing_entry_rejected(self, store):
        glossary = store / "python.glossary"
        glossary.write_text(
            re.sub(
                r"^simple_design — .*\n",
                "",
                glossary.read_text(encoding="utf-8"),
                flags=re.MULTILINE,
            ),
            encoding="utf-8",
        )
        completed = validate(store)
        assert completed.returncode == 1
        assert "glossary entry missing for simple_design" in completed.stderr

    def test_duplicate_entry_rejected(self, store):
        glossary = store / "python.glossary"
        glossary.write_text(
            glossary.read_text(encoding="utf-8") + "simple_design — duplicate\n",
            encoding="utf-8",
        )
        completed = validate(store)
        assert completed.returncode == 1
        assert "duplicate glossary entry for simple_design" in completed.stderr

    def test_out_of_order_entries_rejected(self, store):
        glossary = store / "python.glossary"
        glossary.write_text(
            "waste — deliberately out of order\n"
            + glossary.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        completed = validate(store)
        assert completed.returncode == 1
        assert "out of alphabetical order" in completed.stderr
        assert "abbreviations" in completed.stderr

    def test_entry_syntax_rejected(self, store):
        policy = store / "python.rules"
        policy.write_text(
            policy.read_text(encoding="utf-8") + "simple_design — early\n",
            encoding="utf-8",
        )
        completed = validate(store)
        assert completed.returncode == 1
        assert "simple_design" in completed.stderr
