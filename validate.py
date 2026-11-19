#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "textx==4.4.0",
# ]
# ///
"""Validate Rules and glossary syntax (textX) and their consistency.

Run standalone: uv run --no-project rules/validate.py (no textX in the
project venv needed: uv builds an isolated env from the PEP 723 metadata
above).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from textx import TextXError, metamodel_from_file

ROOT = Path(__file__).parent
RULES_GRAMMAR = ROOT / "rules.tx"
GLOSSARY_GRAMMAR = ROOT / "glossary.tx"
DEFAULT_RULES = ROOT / "python.rules"
DEFAULT_GLOSSARY = ROOT / "python.glossary"


def grammar_literals(mm_rules: object, rule_name: str) -> list[str]:
    rule = mm_rules[rule_name]._tx_peg_rule
    return [node.to_match for node in rule.nodes if type(node).__name__ == "StrMatch"]


def load(mm: object, path: Path) -> tuple[str, list, list[str]]:
    """Read and parse one file. `lines` stays empty whenever `errors` is non-empty."""

    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exception:
        return "", [], [f"{path}: {exception}"]
    if source and not source.endswith("\n"):
        return "", [], [f"{path}: missing final newline"]
    try:
        model = mm.model_from_str(source, file_name=str(path))
    except TextXError as exception:
        return "", [], [f"{path}: {exception}"]
    # An empty model parses to '' instead of an object with .lines.
    lines = [] if isinstance(model, str) else model.lines
    return source, lines, []


def condition_key(condition: object | None) -> tuple | None:
    if condition is None:
        return None
    parts = [(p.op, p.value) for p in condition.rest]
    # AND binds tighter than OR; canonicalize without changing precedence.
    groups: list[list[str]] = [[condition.first]]
    for operator, value in parts:
        if operator == "AND":
            groups[-1].append(value)
        else:
            groups.append([value])
    return tuple(tuple(sorted(group)) for group in groups)


def where(path: Path, source: str, node: object) -> str:
    position = getattr(node, "_tx_position", None)
    line = source.count("\n", 0, position) + 1 if isinstance(position, int) else "?"
    return f"{path}:{line}"


def operator_drift(mm: object) -> str | None:
    known = grammar_literals(mm, "Operator")
    if set(known) == {"PREFER", "USE", "FORBID", "AVOID"}:
        return None
    change = "rules.tx: operator literals changed; update the checks in "
    return change + f"validate.py (grammar has {', '.join(sorted(known))})"


def check_rules(mm: object, path: Path) -> tuple[set[str], list[str]]:
    """Return the symbol names policies use, plus every policy error — one parse."""
    source, lines, errors = load(mm, path)
    if errors:
        return set(), errors
    checker = PolicyCheck(path, source)
    return checker.used, checker.check(lines)


class PolicyCheck:
    """One file's policy checks; the instance carries that file's state."""

    def __init__(self, path: Path, source: str) -> None:
        self.path = path
        self.source = source
        self.scope: str | None = None
        self.errors: list[str] = []
        self.used: set[str] = set()
        self.sections: set[str] = set()
        self.ids: set[str] = set()
        self.signatures: set[tuple] = set()
        self.operators_seen: dict[tuple, set[str]] = {}

    def check(self, lines: list) -> list[str]:
        for node in lines:
            kind = type(node).__name__
            if kind == "Section":
                self.section(node)
            elif kind == "Policy":
                self.policy(node)
        return self.errors

    def section(self, node: object) -> None:
        scope = node.name
        if scope in self.sections:
            self.errors.append(f"{where(self.path, self.source, node)}: duplicate scope [{scope}]")
        self.sections.add(scope)
        self.scope = scope

    def policy(self, node: object) -> None:
        self.used |= self.names(node)
        if self.scope is None:
            self.errors.append(f"{where(self.path, self.source, node)}: policy must follow a [scope]")
            return
        op = node.op
        self.prefix(node)
        self.unique_id(node)
        self.operator_use(node, op)
        self.predicates(node)
        self.duplicate(node, op)
        self.contradiction(node, op)

    def names(self, node: object) -> set[str]:
        used = {node.target}
        if node.alternative:
            used.add(node.alternative)
        for cond in (node.when, node.unless):
            if cond is not None:
                used.add(cond.first)
                used.update(part.value for part in cond.rest)
        return used

    def prefix(self, node: object) -> None:
        scope = self.scope
        if scope is not None and len(scope) >= 2 and node.id[:2] == scope[:2].upper():
            return
        self.errors.append(f"{where(self.path, self.source, node)}: policy id {node.id} does not match the scope {scope}")

    def unique_id(self, node: object) -> None:
        if node.id in self.ids:
            self.errors.append(f"{where(self.path, self.source, node)}: duplicate policy id {node.id}")
        self.ids.add(node.id)

    def operator_use(self, node: object, op: str) -> None:
        mark = where(self.path, self.source, node)
        if op != "PREFER" and node.alternative:
            self.errors.append(f"{mark}: OVER is only valid with PREFER")
        if op == "PREFER" and not node.alternative:
            self.errors.append(f"{mark}: PREFER requires OVER alternative")
        if node.alternative and node.target == node.alternative:
            self.errors.append(f"{mark}: target and alternative must differ")

    def predicates(self, node: object) -> None:
        for label, cond in [("WHEN", node.when), ("UNLESS", node.unless)]:
            if cond is None:
                continue
            values = [cond.first] + [part.value for part in cond.rest]
            if len(values) != len(set(values)):
                self.errors.append(f"{where(self.path, self.source, node)}: repeated predicate in {label}")

    def duplicate(self, node: object, op: str) -> None:
        signature = (
            self.scope,
            node.target,
            condition_key(node.when),
            condition_key(node.unless),
        )
        whole = (*signature, op, node.alternative or "")
        if whole in self.signatures:
            self.errors.append(f"{where(self.path, self.source, node)}: duplicate policy")
        self.signatures.add(whole)

    def contradiction(self, node: object, op: str) -> None:
        signature = (
            self.scope,
            node.target,
            condition_key(node.when),
            condition_key(node.unless),
        )
        seen: set[str] = self.operators_seen.setdefault(signature, set())
        if (op == "USE" and "FORBID" in seen) or (op == "FORBID" and "USE" in seen):
            self.errors.append(f"{where(self.path, self.source, node)}: direct USE/FORBID contradiction for {node.target}")
        seen.add(op)


def check_glossary(mm: object, path: Path) -> tuple[set[str], list[str]]:
    source, lines, errors = load(mm, path)
    if errors:
        return set(), errors

    glossary: dict[str, str] = {}
    previous: str | None = None
    for node in lines:
        if type(node).__name__ != "Entry":
            continue
        position = where(path, source, node)
        if (name := node.name) in glossary:
            errors.append(f"{position}: duplicate glossary entry for {name}")
            continue
        if previous is not None and name < previous:
            errors.append(f"{position}: glossary entry {name} is out of alphabetical order, it belongs before {previous}")
        glossary[name] = position
        previous = name
    return set(glossary), errors


def paths(files: list[Path]) -> tuple[list[Path], list[Path]]:
    rules = [p for p in files if p.suffix == ".rules"] or [DEFAULT_RULES]
    glossary = [p for p in files if p.suffix != ".rules"] or [DEFAULT_GLOSSARY]
    return rules, glossary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grammar", type=Path, default=RULES_GRAMMAR, help="the rules grammar file")
    parser.add_argument("files", nargs="*", type=Path, help="*.rules files")
    args = parser.parse_args(argv)
    rules_paths, glossary_paths = paths(args.files)
    try:
        mm_rules = metamodel_from_file(str(args.grammar), skipws=False)
        mm_glossary = metamodel_from_file(str(GLOSSARY_GRAMMAR), skipws=False)
    except TextXError as exception:
        print(f"Invalid grammar: {exception}", file=sys.stderr)
        return 2
    if (drift := operator_drift(mm_rules)) is not None:
        print(drift, file=sys.stderr)
        return 1
    used, defined, errors = collect(mm_rules, mm_glossary, rules_paths, glossary_paths)
    glossary_path = glossary_paths[0]
    for name in sorted(used - defined):
        errors.append(f"{glossary_path}: glossary entry missing for {name}")
    for name in sorted(defined - used):
        errors.append(f"{glossary_path}: glossary name {name} is not used by any policy")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    for path in [*rules_paths, *glossary_paths]:
        print(f"OK {path}")
    return 0


def collect(
    mm_rules: object, mm_glossary: object, rules_paths: list[Path], glossary_paths: list[Path]
) -> tuple[set[str], set[str], list[str]]:
    """One pass over every file: used policy names, defined glossary names, errors."""
    used: set[str] = set()
    defined: set[str] = set()
    errors: list[str] = []
    for path in rules_paths:
        names, rule_errors = check_rules(mm_rules, path)
        used |= names
        errors.extend(rule_errors)
    for path in glossary_paths:
        names, glossary_errors = check_glossary(mm_glossary, path)
        defined |= names
        errors.extend(glossary_errors)
    return used, defined, errors


if __name__ == "__main__":
    raise SystemExit(main())
