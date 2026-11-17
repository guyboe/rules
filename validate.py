#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "textx==4.4.0",
# ]
# ///
"""Validate Rules syntax (textX) and local consistency.

Run standalone: uv run --no-project rules/validate.py (no textX in the
project venv needed: uv builds an isolated env from the PEP 723 metadata
above).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from textx import TextXError, metamodel_from_file

GRAMMAR = Path(__file__).with_name("rules.tx")


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


def check_file(mm: object, path: Path) -> list[str]:
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
        line_number = (
            source.count("\n", 0, line) + 1 if isinstance(line, int) else "?"
        )
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
                        errors.append(
                            f"{where}: repeated predicate in {label}"
                        )
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="*.rules files")
    args = parser.parse_args(argv)
    paths = args.files or [Path(__file__).with_name("python.rules")]
    try:
        mm = metamodel_from_file(str(GRAMMAR), skipws=False)
    except TextXError as exception:
        print(  # noqa: T201
            f"Invalid grammar {GRAMMAR}: {exception}", file=sys.stderr
        )
        return 2
    errors = [error for path in paths for error in check_file(mm, path)]
    if errors:
        print("\n".join(errors), file=sys.stderr)  # noqa: T201
        return 1
    for path in paths:
        print(f"OK {path}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
