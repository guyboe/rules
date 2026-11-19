# Rule indexes (v1.1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every policy line in `python.rules` carries a mandatory, permanent ID — two uppercase letters (first two letters of the scope) + four digits, e.g. `GE0001`, `EX0002`.

**Architecture:** The ID becomes a required field in the `rules.tx` grammar's
`Policy` rule. `validate.py` gains two checks (prefix match against the scope,
file-wide ID uniqueness). Existing rules get IDs in one migration commit;
`bin/rules`, `semantics.md`, `README.md`, and the OpenCode agent files learn the
protocol.

**Tech Stack:** Python 3.13, textX 4.4.0 (PEP 723 standalone script), pytest via uv.

**Spec:** `docs/superpowers/specs/2026-11-19-rule-indexes-design.md`

## Global Constraints

- ID regex: `[A-Z]{2}[0-9]{4}` — exactly two uppercase letters then exactly four digits.
- Prefix = the scope's first two letters, uppercased. Scopes shorter than two
  letters are a validation error.
- No renumbering, ever: deletion leaves gaps; new rule = max+1 in its letter pool.
- All 17 existing policies keep their order and wording; only the ID prefix is added.
- Language version is `v1.1` in `bin/rules` LANGUAGE and in file headers.
- One rule per physical line stays true; the ID is part of the rule line.

## Review Focus

- One-letter scope like `[a]` → validate must reject with a clear message (pinned
  in Task 1's test: `test_short_scope_rejected`).
- Lowercase or wrong-prefix ID (`ge0001`, `XX0001` in `[general]`) → rejected as
  syntax error (Task 1 grammar test) or prefix mismatch (Task 2 test).
- Duplicate ID in one file → rejected (Task 2 test).
- `show <ID>` works for any prefix, not just GE (Task 4 test with EX prefix).
- `parse_policy` must not treat an ID-only line as a section or lose it (Task 3
  regression via existing CLI tests).

---

### Task 1: Grammar — mandatory ID in Policy

**Files:**
- Modify: `rules.tx`
- Test: run through `uv run --no-project validate.py` (no unit test file changes)

**Interfaces:**
- Produces: `Policy.id` (str) attribute on every parsed policy; used by
  `validate.py` in Task 2 and by migration in Task 3.

- [ ] **Step 1: Update `rules.tx`**

Policy rule becomes:

```textX
Policy:
    H id=ID WS op=Operator WS target=Name
    (WS 'OVER' WS alternative=Name)?
    (WS 'WHEN' WS when=Condition)?
    (WS 'UNLESS' WS unless=Condition)?
    H EOL
;
```

And add, next to `Operator`:

```textX
ID:
    /[A-Z]{2}[0-9]{4}/
;
```

Bump the header comment to `Rules v1.1`.

- [ ] **Step 2: Verify the grammar parses an ID-bearing line and rejects a bare one**

Run: `uv run --no-project -c "pass" 2>/dev/null || true` — instead verify
directly with python:

```bash
uv run --no-project --with textx==4.4.0 python -c "
from textx import metamodel_from_file
mm = metamodel_from_file('rules.tx', skipws=False)
m = mm.model_from_str('[general]\nGE0001 PREFER x OVER y WHEN z\n')
p = [l for l in m.lines if type(l).__name__=='Policy'][0]
assert p.id == 'GE0001', p.id
try:
    mm.model_from_str('[general]\nPREFER x OVER y WHEN z\n')
except Exception as e:
    print('rejected bare line: OK')
"
```

Expected: prints `rejected bare line: OK`, no assertion error.

### Task 2: Validator — prefix and uniqueness checks

**Files:**
- Modify: `validate.py` (in `check_rules`, the `elif kind == "Policy":` branch)
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `Policy.id` from Task 1.
- Produces: error messages `"{where}: policy id {id} does not match the scope {scope}"` and `"{where}: duplicate policy id {id}"`. `used_names_in_rules` /
  `check_rules` signatures unchanged.

- [ ] **Step 1: Write failing tests in `tests/test_validate.py`, new class `TestIdChecks`**

Using the existing `store` fixture and `validate()` helper, each test writes a
one-rule policy + the probe glossary line `probe.x — the probe target\n`:

- `test_missing_id_rejected`: policy `[a]\nPREFER x OVER y\n` → rc 1, stderr mentions `PREFER` (textX syntax failure for no ID).
- `test_wrong_prefix_rejected`: `[general]\nXX0101 PREFER x OVER y WHEN z\n` → rc 1, `does not match the scope general`.
- `test_lowercase_prefix_rejected`: `[general]\nge0101 PREFER x OVER y WHEN z\n` → rc 1 (textX syntax).
- `test_short_scope_rejected`: `[g]\nGG0101 PREFER x OVER y WHEN z\n` → rc 1, `does not match the scope g`.
- `test_duplicate_id_rejected`: `[general]\nGE0101 PREFER x OVER y WHEN z\n` + `[types]\nGE0102 USE x WHEN z\n` → rc 1, `duplicate policy id GE0101`.

Note: with a duplicate the reported ID pair is the second line — the message
covers both, assert on `duplicate policy id`.

- [ ] **Step 2: Run tests, verify each fails for the right reason**

Run: `uv run --no-project --with pytest pytest tests/test_validate.py::TestIdChecks -v -m manual`
Expected: FAIL (the checks do not exist yet; `test_missing_id_rejected` may
already fail identically after Task 1).

- [ ] **Step 3: Implement in `check_rules`**

In the `Policy` branch, after the `scope is None` guard and before the operator
checks:

```python
prefix = node.id[:2]
expected = scope[:2].upper()
if len(scope) < 2 or prefix != expected:
    errors.append(f"{where}: policy id {node.id} does not match the scope {scope}")
if node.id in seen_ids:
    errors.append(f"{where}: duplicate policy id {node.id}")
seen_ids.add(node.id)
```

`seen_ids: set[str] = set()` initialized beside `seen_rules`.

- [ ] **Step 4: Run the shipped default policy, verify still OK**

Run: `uv run --no-project validate.py python.rules python.glossary`
Expected: fails now — `python.rules` has no IDs yet. That is the Task 3 trigger,
so this step expects the ID-mismatch error output.

- [ ] **Step 5: Run TestIdChecks, verify PASS**

Run: `uv run --no-project --with pytest pytest tests/test_validate.py::TestIdChecks -v -m manual`
Expected: PASS

### Task 3: Migration — ID every existing rule

**Files:**
- Modify: `python.rules`
- Test: `tests/test_validate.py` (shipped-policy test asserts IDs)

**Interfaces:**
- Produces: the canonical ID assignment other tasks' tests rely on: GE0001,
  GE0002, GE0003, FI0001, AR0001, EX0001, EX0002, MO0001, MO0002, NA0001,
  NA0002, TY0001, TY0002, DO0001, DO0002, PO0001.

- [ ] **Step 1: Rewrite `python.rules` with IDs in place, in this exact order:**

```text
# Rules v1.1 — one rule per line; each rule starts with its ID.
# Symbol explanations live in python.glossary (grammar: glossary.tx).
[general]
GE0001 PREFER simple_design OVER deduplication WHEN principles_conflict
GE0002 AVOID speculative_abstractions
GE0003 PREFER walrus_operator OVER separate_assignment_and_check WHEN assignment_immediately_precedes_condition AND assigned_value_is_reused

[filesystem]
FI0001 PREFER pathlib.Path OVER os.path WHEN manipulating_filesystem_paths

[architecture]
AR0001 PREFER classes OVER functions UNLESS stateless_leaf

[exceptions]
EX0001 FORBID bare_except
EX0002 USE contextlib.suppress WHEN only_suppression_needed

[models]
MO0001 USE direct_attribute_access WHEN accessing_declared_pydantic_or_dataclass_fields
MO0002 FORBID getattr_or_dict_get WHEN accessing_declared_pydantic_or_dataclass_fields

[naming]
NA0001 PREFER single_word_names OVER multi_word_names WHEN naming_variables
NA0002 FORBID abbreviations WHEN naming_variables UNLESS established_it_abbreviation OR single_letter_name

[types]
TY0001 PREFER enum.StrEnum_with_auto OVER bare_string_literals WHEN string_values_compared_or_matched
TY0002 USE type_hints WHEN writing_function_signatures

[documentation]
DO0001 AVOID docstrings WHEN purpose_evident_from_name_and_parameters
DO0002 AVOID comments UNLESS explains_non_obvious_constraint

[policy]
PO0001 FORBID project_specific_rules
```

- [ ] **Step 2: Validate the store**

Run: `uv run --no-project validate.py python.rules python.glossary`
Expected: `OK python.rules` and `OK python.glossary`, rc 0.

- [ ] **Step 3: Full manual test suite**

Run: `uv run --no-project --with pytest pytest tests -q -m manual`
Expected: FAIL only where tests pin ID-less lines (Task 6 fixes them); the
TestIdChecks class passes.

### Task 4: CLI — language bump and show-by-ID

**Files:**
- Modify: `bin/rules` (docstring unchanged otherwise; `LANGUAGE = "v1.1"`)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `parse_policy` untouched; `show` needs no code change.
- Produces: `rules show EX0001` prints that line.

- [ ] **Step 1: Write failing test in `TestShow`**

```python
def test_show_by_id(self, store):
    result = run(store, "show", "EX0001")
    assert result.returncode == 0
    assert result.stdout.strip().splitlines() == [
        "EX0001 FORBID bare_except"
    ]
```

- [ ] **Step 2: Run, verify FAIL**

Run: `uv run --no-project --with pytest pytest tests/test_cli.py::TestShow::test_show_by_id -v -m manual`
Expected: FAIL — the fixture store still carries ID-less rules, so `show EX0001` reports `unknown topic`.

- [ ] **Step 3: Bump `LANGUAGE = "v1.1"` in `bin/rules`**

- [ ] **Step 4: Run, verify PASS (after Task 3's rewrite is in the fixture store — it copies `python.rules` from ROOT, so it comes along)**

Same command. Expected: PASS.

- [ ] **Step 5: Version line test update**

In `TestWake.test_wake_prints_version_line` change `RULES v1.0 @` → `RULES v1.1 @`.

### Task 5: Documentation — semantics, README, agent files

**Files:**
- Modify: `semantics.md`, `README.md`, `agents/opencode/embed.md`, `agents/opencode/rules.add.md`

**Interfaces:**
- Produces: the editing protocol for IDs that the store's own contributors follow.

- [ ] **Step 1: `semantics.md`**

Header `Rules v1.0 — LLM contract` → `Rules v1.1 — LLM contract`. In
*Interpretation*, after the line about "ONE physical line", add:

> - Every policy line starts with its ID: two uppercase letters (the first two
>   letters of the scope) then four digits, e.g. `EX0002`. Cite rules by ID, as in
>   `rules show EX0002`.

In *Editing protocol*, insert after step 3 (or as new numbered item):

> - Assign the ID once and never renumber: deleting a policy leaves its ID
>   retired; a new policy takes the next free number in its letter pool
>   (`max + 1`), even after gaps.

- [ ] **Step 2: `README.md`**

In *Change a rule* step 2, append: `Keep each policy line starting with its
permanent ID (scope prefix + next number; never renumber).` Update the
`rules show <target>` row: add `rules show <ID>` — *Print the policy with that
ID* (same row or a new one, matching table style).

- [ ] **Step 3: `agents/opencode/rules.add.md`**

Stage 1 item 2, after "Pick the most fitting existing scope.": add `Assign the next free ID in that scope's two-letter pool (max existing + 1).` Stage 2 step 6, after "Add the rule line": add `use the proposed ID`. Present step (item 4) — mention the ID in the presented rule line, no protocol change needed.

- [ ] **Step 4: `agents/opencode/embed.md`**

In the second bullet (edit-the-policy one), after "Keep one rule per line.": insert `Start every rule line with its permanent ID (never renumber).`

### Task 6: Test alignment — ID-bearing lines in policy-pinning tests

**Files:**
- Modify: `tests/test_validate.py` (TestPythonRules, TestOperatorsFromGrammar.drift_store calls), `tests/test_cli.py` (line-pinning asserts)

**Interfaces:**
- Consumes: canonical IDs from Task 3.

- [ ] **Step 1: `TestPythonRules` regexes anchor the ID**

`test_strenum_rule_present`: pattern
`^PREFER enum\.StrEnum_with_auto` → `^TY0001 PREFER enum\.StrEnum_with_auto`;
`[types]` assert unchanged (it matches the plain section header).
`test_documentation_rule_present`: `^AVOID docstrings` → `^DO0001 AVOID docstrings`.

- [ ] **Step 2: `TestOperatorsFromGrammar.drift_store` policies gain IDs**

The three `policy=...` strings: `MUST probe.x` → `MU0001 MUST probe.x` (added
operator) and `MAY probe.x` → `MA0001 MAY probe.x` (renamed operator); their
scopes `[general]` / `[naming]` make these prefixes valid. The
`test_shipped_grammar_matches_checks` test needs no change (validate uses the
real rules file).

Note: the renamed-operator test writes glossary `probe.x — the probe target\n`
only — with only MU/MA prefix policies, no more glossary churn needed.

- [ ] **Step 3: `tests/test_cli.py` line assertions**

- `TestWake.test_wake_prints_policy`: `"PREFER simple_design OVER deduplication"` → `"GE0001 PREFER simple_design OVER deduplication"` (substring match works with the ID in place).
- `TestShow.test_show_scope_prints_policies`: assert substring `"FI0001 PREFER pathlib.Path OVER os.path"` replacing the old substring.
- `TestShow.test_show_target_prints_matching_line`: `"FORBID getattr_or_dict_get"` → `"MO0002 FORBID getattr_or_dict_get"`.
- `TestShow.test_show_target_ignores_glossary`: expected line list gains `MO0002 ` prefix.
- `TestShow.test_show_scope_ignores_glossary`: `"AVOID docstrings"` stays (substring of the ID-bearing line), no change.
- `TestValidate.test_validate_rejects_broken_policy`: policy `[a]\nPREFER x\n` → `[a]\nAA0001 PREFER x\n` so the failure stays "PREFER requires OVER" (scope [a] is 1 letter — with correct prefix check AA0001 vs scope `a` this would ALSO break, so use a 2-letter scope and message check: change to `[aa]\nAA0001 PREFER x\n` and assert "PREFER requires OVER" still in stderr).

- [ ] **Step 4: Full manual suite green**

Run: `uv run --no-project --with pytest pytest tests -q -m manual`
Expected: all PASS including shipped-policy checks.

- [ ] **Step 5: Commit the store**

```bash
git add python.rules rules.tx validate.py bin/rules semantics.md README.md agents/opencode/embed.md agents/opencode/rules.add.md tests/
git add validate.py docs/superpowers/specs/2026-11-19-rule-indexes-design.md docs/superpowers/plans/2026-11-19-rule-indexes.md
git commit -m "feat(rules): permanent rule IDs (v1.1)"
```
