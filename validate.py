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


def used_names_in_rules(mm_rules: object, path: Path) -> tuple[set[str], list[str]]:
    """Return the symbol names policies use, plus syntax errors."""
    errors = check_rules(mm_rules, path)
    try:
        source = path.read_text(encoding="utf-8")
        model = mm_rules.model_from_str(source, file_name=str(path))
    except (OSError, TextXError):
        return set(), errors
    used: set[str] = set()
    for node in model.lines:
        if type(node).__name__ != "Policy":
            continue
        used.add(node.target)
        if node.alternative:
            used.add(node.alternative)
        for cond in (node.when, node.unless):
            if cond is not None:
                used.add(cond.first)
                used.update(part.value for part in cond.rest)
    return used, errors


def check_rules(mm: object, path: Path) -> list[str]:
    errors: list[str] = []
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exception:
        return [f"{path}: {exception}"]
    if source and not source.endswith("\n"):
        return [f"{path}: missing final newline"]
    try:
        model = mm.model_from_str(source, file_name=str(path))
    except TextXError as exception:
        return [f"{path}: {exception}"]

    scope: str | None = None
    seen_sections: set[str] = set()
    seen_rules: set[tuple] = set()
    policies: dict[tuple, set[str]] = {}

    for node in model.lines:
        kind = type(node).__name__
        line = getattr(node, "_tx_position", None)
        line_number = source.count("\n", 0, line) + 1 if isinstance(line, int) else "?"
        where = f"{path}:{line_number}"
        if kind == "Section":
            scope = node.name
            if scope in seen_sections:
                errors.append(f"{where}: duplicate scope [{scope}]")
            seen_sections.add(scope)
        elif kind == "Policy":
            if scope is None:
                errors.append(f"{where}: policy must follow a [scope]")
                continue
            if node.op != "PREFER" and node.alternative:
                errors.append(f"{where}: OVER is only valid with PREFER")
            if node.op == "PREFER" and not node.alternative:
                errors.append(f"{where}: PREFER requires OVER alternative")
            if node.alternative and node.target == node.alternative:
                errors.append(f"{where}: target and alternative must differ")
            for label, cond in [("WHEN", node.when), ("UNLESS", node.unless)]:
                if cond is not None:
                    values = [cond.first] + [part.value for part in cond.rest]
                    if len(values) != len(set(values)):
                        errors.append(f"{where}: repeated predicate in {label}")
            signature = (
                scope,
                node.target,
                condition_key(node.when),
                condition_key(node.unless),
            )
            whole = (*signature, node.op, node.alternative or "")
            if whole in seen_rules:
                errors.append(f"{where}: duplicate policy")
            seen_rules.add(whole)
            operators = policies.setdefault(signature, set())
            if (node.op == "USE" and "FORBID" in operators) or (
                node.op == "FORBID" and "USE" in operators
            ):
                errors.append(
                    f"{where}: direct USE/FORBID contradiction for {node.target}"
                )
            operators.add(node.op)
    return errors


def check_glossary(mm: object, path: Path) -> list[str]:
    errors: list[str] = []
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exception:
        return [f"{path}: {exception}"]
    if source and not source.endswith("\n"):
        return [f"{path}: missing final newline"]
    try:
        model = mm.model_from_str(source, file_name=str(path))
    except TextXError as exception:
        return [f"{path}: {exception}"]

    glossary: dict[str, int | str] = {}
    previous: str | None = None
    for node in model.lines:
        if type(node).__name__ != "Entry":
            continue
        line = getattr(node, "_tx_position", None)
        line_number = source.count("\n", 0, line) + 1 if isinstance(line, int) else "?"
        where = f"{path}:{line_number}"
        name = node.name
        if name in glossary:
            errors.append(f"{where}: duplicate glossary entry for {name}")
            continue
        if previous is not None and name < previous:
            errors.append(
                f"{where}: glossary entry {name} is out of alphabetical "
                f"order, it belongs before {previous}"
            )
        glossary[name] = line_number
        previous = name
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="*.rules files")
    args = parser.parse_args(argv)
    rules_paths = [p for p in args.files if p.suffix == ".rules"] or [DEFAULT_RULES]
    glossary_paths = [p for p in args.files if p.suffix != ".rules"] or [
        DEFAULT_GLOSSARY
    ]
    try:
        mm_rules = metamodel_from_file(str(RULES_GRAMMAR), skipws=False)
        mm_glossary = metamodel_from_file(str(GLOSSARY_GRAMMAR), skipws=False)
    except TextXError as exception:
        print(  # noqa: T201
            f"Invalid grammar: {exception}", file=sys.stderr
        )
        return 2

    errors: list[str] = []
    used: set[str] = set()
    defined: set[str] = set()
    for path in rules_paths:
        names, rule_errors = used_names_in_rules(mm_rules, path)
        used |= names
        errors.extend(rule_errors)
    for path in glossary_paths:
        errors.extend(check_glossary(mm_glossary, path))
        try:
            source = path.read_text(encoding="utf-8")
            model = mm_glossary.model_from_str(source, file_name=str(path))
        except (OSError, TextXError):
            continue
        defined.update(
            node.name for node in model.lines if type(node).__name__ == "Entry"
        )

    glossary_path = glossary_paths[0]
    for name in sorted(used - defined):
        errors.append(f"{glossary_path}: glossary entry missing for {name}")
    for name in sorted(defined - used):
        errors.append(
            f"{glossary_path}: glossary name {name} is not used by any policy"
        )

    if errors:
        print("\n".join(errors), file=sys.stderr)  # noqa: T201
        return 1
    for path in [*rules_paths, *glossary_paths]:
        print(f"OK {path}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
