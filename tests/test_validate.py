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

    def test_block_present(self) -> None:
        assert pep723_block(VALIDATE.read_text(encoding="utf-8")), "PEP 723 script block missing"

    def test_textx_pinned(self) -> None:
        block = pep723_block(VALIDATE.read_text(encoding="utf-8"))
        assert block and "textx==4.4.0" in block

    def test_requires_python(self) -> None:
        block = pep723_block(VALIDATE.read_text(encoding="utf-8"))
        assert block and 'requires-python = ">=3.13"' in block

    def test_docstring_mentions_uv_run(self) -> None:
        header = VALIDATE.read_text(encoding="utf-8")[:400]
        assert "uv run" in header


class TestUvRun:
    """uv run executes the standalone validator without the project venv."""

    def test_validate_ok(self) -> None:
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

    def test_strenum_rule_present(self) -> None:
        rules = (RULES_DIR / "python.rules").read_text(encoding="utf-8")
        assert re.search(r"^\[types\]\s*$", rules, re.MULTILINE), "scope [types] missing"
        assert re.search(
            r"^TY0001 PREFER enum\.StrEnum_with_auto OVER bare_string_literals"
            r" WHEN string_values_compared_or_matched\s*$",
            rules,
            re.MULTILINE,
        ), "StrEnum policy line missing"

    def test_documentation_rule_present(self) -> None:
        rules = (RULES_DIR / "python.rules").read_text(encoding="utf-8")
        assert re.search(r"^\[documentation\]\s*$", rules, re.MULTILINE)
        assert re.search(
            r"^DO0001 AVOID docstrings"
            r" WHEN purpose_evident_from_name_and_parameters\s*$",
            rules,
            re.MULTILINE,
        )


class TestIdChecks:
    """Every policy line carries a scope-derived, unique ID."""

    @staticmethod
    def id_store(store: Path, policy: str) -> subprocess.CompletedProcess[str]:
        (store / "python.rules").write_text(policy, encoding="utf-8")
        (store / "python.glossary").write_text(
            "target.x — the probe target\ntarget.y — probe\nunique.z — probe\nty — probe\n",
            encoding="utf-8",
        )
        return validate(store)

    def test_missing_id_rejected(self, store: Path) -> None:
        completed = self.id_store(store, "[general]\nPREFER target.x OVER target.y WHEN unique.z\n")
        assert completed.returncode == 1

    def test_wrong_prefix_rejected(self, store: Path) -> None:
        completed = self.id_store(store, "[general]\nXX0101 PREFER target.x OVER target.y WHEN unique.z\n")
        assert completed.returncode == 1
        assert "policy id XX0101 does not match the scope general" in completed.stderr

    def test_lowercase_prefix_rejected(self, store: Path) -> None:
        completed = self.id_store(store, "[general]\nge0101 PREFER target.x OVER target.y WHEN unique.z\n")
        assert completed.returncode == 1

    def test_short_scope_rejected(self, store: Path) -> None:
        completed = self.id_store(store, "[g]\nGG0101 PREFER target.x OVER target.y WHEN unique.z\n")
        assert completed.returncode == 1
        assert "policy id GG0101 does not match the scope g" in completed.stderr

    def test_duplicate_id_rejected(self, store: Path) -> None:
        completed = self.id_store(
            store,
            "[general]\nGE0101 PREFER target.x OVER target.y WHEN unique.z\n\n[testing]\nGE0101 USE target.x WHEN ty\n",
        )
        assert completed.returncode == 1
        assert "duplicate policy id GE0101" in completed.stderr


def validate(store: Path, grammar: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [
        "uv",
        "run",
        "--no-project",
        str(VALIDATE),
    ]
    if grammar is not None:
        command += ["--grammar", str(grammar)]
    command += [
        str(store / "python.rules"),
        str(store / "python.glossary"),
    ]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


class TestGlossaryFile:
    """python.glossary carries the per-symbol explanations."""

    def test_marker_present(self) -> None:
        rules = (RULES_DIR / "python.rules").read_text(encoding="utf-8")
        assert "GLOSSARY" not in rules
        assert (RULES_DIR / "python.glossary").is_file()

    def test_entries_present(self) -> None:
        glossary = (RULES_DIR / "python.glossary").read_text(encoding="utf-8")
        assert re.search(r"^simple_design — \S", glossary, re.MULTILINE)
        assert re.search(
            r"^purpose_evident_from_name_and_parameters — \S",
            glossary,
            re.MULTILINE,
        )

    def test_entries_alphabetical(self) -> None:
        glossary = (RULES_DIR / "python.glossary").read_text(encoding="utf-8")
        names = [line.split(" — ")[0] for line in glossary.splitlines() if " — " in line and not line.startswith("#")]
        assert names == sorted(names)


class TestGlossaryValidation:
    """The validator enforces the glossary/policy contract and the order."""

    def test_unknown_entry_rejected(self, store: Path) -> None:
        glossary = store / "python.glossary"
        glossary.write_text(
            "zzz_suffix — unused\n",  # alphabetically last, keeps order valid
            encoding="utf-8",
        )
        completed = validate(store)
        assert completed.returncode == 1
        assert "not used by any policy" in completed.stderr

    def test_missing_entry_rejected(self, store: Path) -> None:
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

    def test_duplicate_entry_rejected(self, store: Path) -> None:
        glossary = store / "python.glossary"
        glossary.write_text(
            glossary.read_text(encoding="utf-8") + "simple_design — duplicate\n",
            encoding="utf-8",
        )
        completed = validate(store)
        assert completed.returncode == 1
        assert "duplicate glossary entry for simple_design" in completed.stderr

    def test_out_of_order_entries_rejected(self, store: Path) -> None:
        glossary = store / "python.glossary"
        glossary.write_text(
            "waste — deliberately out of order\n" + glossary.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        completed = validate(store)
        assert completed.returncode == 1
        assert "out of alphabetical order" in completed.stderr
        assert "abbreviations" in completed.stderr

    def test_entry_syntax_rejected(self, store: Path) -> None:
        policy = store / "python.rules"
        policy.write_text(
            policy.read_text(encoding="utf-8") + "simple_design — early\n",
            encoding="utf-8",
        )
        completed = validate(store)
        assert completed.returncode == 1
        assert "simple_design" in completed.stderr


PROBE = "target.x — the probe target\ntarget.y — probe\nunique.z — probe\n"


def store_files(store: Path, rules: str, glossary: str = PROBE) -> Path:
    (store / "python.rules").write_text(rules, encoding="utf-8")
    (store / "python.glossary").write_text(glossary, encoding="utf-8")
    return store


def validate_files(
    store: Path, *paths: Path, grammar: Path | None = None
) -> subprocess.CompletedProcess[str]:
    command = ["uv", "run", "--no-project", str(VALIDATE)]
    if grammar is not None:
        command += ["--grammar", str(grammar)]
    command += [str(path) for path in paths]
    return subprocess.run(command, capture_output=True, text=True, check=False)


class TestStructureChecks:
    """The policy structure checks one line at a time."""

    def test_duplicate_scope_rejected(self, store: Path) -> None:
        store_files(store, "[general]\nGE0101 USE target.x\n\n[general]\nGE0102 USE target.y\n")
        completed = validate(store)
        assert completed.returncode == 1
        assert "duplicate scope [general]" in completed.stderr

    def test_policy_before_scope_rejected(self, store: Path) -> None:
        store_files(store, "GE0101 USE target.x\n\n[general]\n")
        completed = validate(store)
        assert completed.returncode == 1
        assert "policy must follow a [scope]" in completed.stderr

    def test_over_with_non_prefer_rejected(self, store: Path) -> None:
        store_files(store, "[general]\nGE0101 USE target.x OVER target.y\n")
        completed = validate(store)
        assert completed.returncode == 1
        assert "OVER is only valid with PREFER" in completed.stderr

    def test_prefer_without_over_rejected(self, store: Path) -> None:
        store_files(store, "[general]\nGE0101 PREFER target.x\n")
        completed = validate(store)
        assert completed.returncode == 1
        assert "PREFER requires OVER alternative" in completed.stderr

    def test_alternative_equals_target_rejected(self, store: Path) -> None:
        store_files(store, "[general]\nGE0101 PREFER target.x OVER target.x\n")
        completed = validate(store)
        assert completed.returncode == 1
        assert "target and alternative must differ" in completed.stderr

    def test_repeated_predicate_rejected(self, store: Path) -> None:
        store_files(store, "[general]\nGE0101 USE target.x WHEN unique.z AND unique.z\n")
        completed = validate(store)
        assert completed.returncode == 1
        assert "repeated predicate in WHEN" in completed.stderr

    def test_empty_rules_accepted(self, store: Path) -> None:
        store_files(store, "", "")
        completed = validate(store)
        assert completed.returncode == 0, completed.stderr
        assert "OK" in completed.stdout

    def test_empty_glossary_rejects_used_name(self, store: Path) -> None:
        store_files(store, "[general]\nGE0101 USE target.x\n", "")
        completed = validate(store)
        assert completed.returncode == 1
        assert "glossary entry missing for target.x" in completed.stderr

    def test_glossary_missing_final_newline_rejected(self, store: Path) -> None:
        (store / "python.rules").write_text("[general]\nGE0101 USE target.x\n", encoding="utf-8")
        (store / "python.glossary").write_text("target.x — the probe target", encoding="utf-8")
        completed = validate(store)
        assert completed.returncode == 1
        assert f"{store / 'python.glossary'}: missing final newline" in completed.stderr

    def test_duplicate_scope_stays_current(self, store: Path) -> None:
        store_files(
            store,
            "[general]\nGE0101 USE target.x\n\n[testing]\nTE0101 USE target.x\n\n[general]\nGE0102 USE target.y\n",
            "target.x — probe\ntarget.y — probe\n",
        )
        completed = validate(store)
        assert completed.returncode == 1
        assert completed.stderr.count("duplicate scope [general]") == 1
        assert "must follow a [scope]" not in completed.stderr
        assert "does not match the scope" not in completed.stderr


class TestSignatureChecks:
    """The whole-policy signature checks: duplicates, contradictions, newline."""

    def test_duplicate_policy_rejected(self, store: Path) -> None:
        store_files(store, "[general]\nGE0101 USE target.x\nGE0102 USE target.x\n")
        completed = validate(store)
        assert completed.returncode == 1
        assert "duplicate policy" in completed.stderr

    def test_duplicate_policy_ignores_condition_order(self, store: Path) -> None:
        store_files(
            store,
            "[general]\nGE0101 USE target.x WHEN unique.z AND target.y\nGE0102 USE target.x WHEN target.y AND unique.z\n",
        )
        completed = validate(store)
        assert completed.returncode == 1
        assert "duplicate policy" in completed.stderr

    def test_distinct_alternatives_allowed(self, store: Path) -> None:
        store_files(
            store,
            "[general]\nGE0101 PREFER target.x OVER target.y\nGE0102 PREFER target.x OVER unique.z\n",
        )
        completed = validate(store)
        assert completed.returncode == 0, completed.stderr

    def test_and_or_conditions_are_distinct(self, store: Path) -> None:
        store_files(
            store,
            "[general]\nGE0101 USE target.x WHEN unique.z AND target.y\nGE0102 USE target.x WHEN unique.z OR target.y\n",
        )
        completed = validate(store)
        assert completed.returncode == 0, completed.stderr

    def test_use_forbid_contradiction_rejected(self, store: Path) -> None:
        store_files(store, "[general]\nGE0101 USE target.x\nGE0102 FORBID target.x\n")
        completed = validate(store)
        assert completed.returncode == 1
        assert "direct USE/FORBID contradiction for target.x" in completed.stderr

    def test_forbid_use_contradiction_rejected(self, store: Path) -> None:
        store_files(store, "[general]\nGE0101 FORBID target.x\nGE0102 USE target.x\n")
        completed = validate(store)
        assert completed.returncode == 1
        assert "direct USE/FORBID contradiction for target.x" in completed.stderr

    def test_missing_final_newline_rejected(self, store: Path) -> None:
        store_files(store, "[general]\nGE0101 USE target.x")
        completed = validate(store)
        assert completed.returncode == 1
        assert "missing final newline" in completed.stderr

    def test_broken_rules_report_glossary_unused(self, store: Path) -> None:
        store_files(store, "[general]\nGE0101 PREFER\n")
        completed = validate(store)
        assert completed.returncode == 1
        assert str(store / "python.rules") in completed.stderr
        assert "glossary name target.x is not used by any policy" in completed.stderr

    def test_errors_name_the_failing_file(self, store: Path) -> None:
        (store / "good.rules").write_text("[general]\nGE0101 USE target.x\n", encoding="utf-8")
        (store / "bad.rules").write_text("[general]\nGE0101 PREFER\n", encoding="utf-8")
        completed = validate_files(store, store / "good.rules", store / "bad.rules")
        assert completed.returncode == 1
        assert "bad.rules" in completed.stderr
        assert "good.rules" not in completed.stderr


class TestOperatorsFromGrammar:
    """validate.py takes the operator literals from rules.tx, not from a copy."""

    @staticmethod
    def drift_store(store: Path, old: str, new: str, policy: str) -> Path:
        grammar = (RULES_DIR / "rules.tx").read_text(encoding="utf-8")
        (store / "rules.tx").write_text(grammar.replace(old, new), encoding="utf-8")
        (store / "python.rules").write_text(policy, encoding="utf-8")
        (store / "python.glossary").write_text(
            "target.x — the probe target\n",
            encoding="utf-8",
        )
        return store

    def test_added_operator_warns_to_update_checks(self, store: Path) -> None:
        self.drift_store(
            store,
            "'USE' | 'PREFER' | 'AVOID' | 'FORBID'",
            "'USE' | 'PREFER' | 'AVOID' | 'MUST' | 'FORBID'",
            "[general]\nGE0101 MUST target.x\n",
        )
        completed = validate(store, grammar=store / "rules.tx")
        assert completed.returncode == 1
        assert "operator literals changed" in completed.stderr

    def test_renamed_operator_fails_loud(self, store: Path) -> None:
        self.drift_store(
            store,
            "'USE' | 'PREFER' | 'AVOID' | 'FORBID'",
            "'USE' | 'MAY' | 'AVOID' | 'FORBID'",
            "[naming]\nNA0101 MAY target.x\n",
        )
        completed = validate(store, grammar=store / "rules.tx")
        assert completed.returncode != 0
        assert "operator literals changed" in completed.stderr

    def test_shipped_grammar_matches_checks(self, store: Path) -> None:
        completed = validate(store, grammar=RULES_DIR / "rules.tx")
        assert completed.returncode == 0, completed.stderr

    def test_operator_drift_reported_once_for_many_files(self, store: Path) -> None:
        self.drift_store(
            store,
            "'USE' | 'PREFER' | 'AVOID' | 'FORBID'",
            "'USE' | 'PREFER' | 'AVOID' | 'MUST' | 'FORBID'",
            "[general]\nGE0101 MUST target.x\n",
        )
        second = store / "second.rules"
        second.write_text("[general]\nGE0101 MUST target.y\n", encoding="utf-8")
        completed = validate_files(
            store, store / "python.rules", second, grammar=store / "rules.tx"
        )
        assert completed.returncode == 1
        assert completed.stderr.count("operator literals changed") == 1
