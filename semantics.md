# Rules v1.0 — LLM contract

**Purpose:** guide Python implementation choices, not validate Python source code.
Read `rules.tx` as the definitive syntax. Read `python.rules` as the active policy.

## Interpretation

- Every policy is ONE physical line inside the preceding `[scope]`. No line continuation, no trailing `;`, no quoted strings, no inline comments.
- `USE X`: X is required when applicable. `PREFER X OVER Y`: choose X rather than Y by default. `AVOID X`: avoid X by default. `FORBID X`: do not use X in the applicable context.
- `WHEN C`: apply the policy only if C is true. `UNLESS C`: do not apply it if C is true. Both may coexist. Effective applicability is `WHEN and not UNLESS`.
- A condition is a sequence of named predicates joined by `AND`/`OR`. `AND` binds tighter than `OR`. Parentheses and negation are intentionally unsupported. Split complicated rules into simple independent policies.
- Names like `shared_mutable_state` are *semantic predicates* interpreted from the coding task, not built-in executable expressions. Avoid opaque abbreviations. The grammar guarantees syntax, not universal semantic truth.
- Scopes are topic labels, not a formal hierarchy. Use the most appropriate scope.
- Prefer a narrower applicable instruction over a generic preference. Do not resolve irreconcilable mandatory/forbidden conflicts by guessing. Ask for clarification.
- `USE`/`FORBID` are strict instructions, `PREFER`/`AVOID` are defaults. Do not reinterpret a preference as an absolute constraint.

## Editing protocol

When the user **explicitly requests a persistent rule change**:
1. Read existing rules and this file. Do not automatically persist incidental coding discussion.
2. Express exactly the requested preference using `USE`, `PREFER`, `AVOID`, `FORBID`, optionally `OVER`, `WHEN`, `UNLESS`. Keep one rule per line.
3. Reuse existing scopes, targets, and conditions when equivalent. Avoid duplicates. Preserve all unrelated policies.
4. Replace superseded rules instead of appending contradictory copies. Do not silently introduce new exceptions or broader prohibitions.
5. If a significant ambiguity cannot be safely resolved, ask rather than inventing meaning.
6. Keep a final newline. Run `rules validate` before committing.

## Examples and intent

`PREFER walrus_operator OVER separate_assignment_and_check WHEN assignment_immediately_precedes_condition AND assigned_value_is_reused`: the rule name names the case. Use `if value := read():` rather than `value = read()` followed immediately by `if value:`, when the bound value is used again below. Do not rewrite code if that harms clarity or changes evaluation semantics.

`USE direct_attribute_access WHEN accessing_declared_pydantic_or_dataclass_fields`: use `obj.field`. Do not use `getattr(obj, 'field', ...)`, `obj.__dict__.get('field')`, or dictionary-style `.get()` to access **declared model fields**. Ordinary dictionaries, truly dynamic fields, and mappings are not model fields.

`PREFER single_word_names OVER multi_word_names WHEN naming_variables`: prefer a variable named `count` over `notification_count`. `pool_size` remains acceptable when a one-word name would hurt clarity. Full short words win over both compounds (`connection_pool_size`) and abbreviations (`cnt`).

`FORBID abbreviations WHEN naming_variables UNLESS established_it_abbreviation OR single_letter_name`: `idx`, `cnt`, `buf`, `temp` are violations — write `index`, `count`, `buffer`. Allowed are abbreviations that are the de-facto IT term (`url`, `id`, `db`, `api`, `http`) and single-letter names (`i`, `j`, `n` for loop counters, `x`/`y` coordinates). Applies to new code and renames. Existing committed names are not retroactively rewritten.

`PREFER enum.StrEnum_with_auto OVER bare_string_literals WHEN string_values_compared_or_matched`: values that participate in comparisons or matching are better carried as `enum.StrEnum` members with `enum.auto()`. Examples: `if kind == "low"`, `side == "long"`, config switches; see `utils/commands.py` (`SettingsType`) and `models/base.py` (`TimeFrame`). Plain string constants stay fine for values never compared (formatting, parsing, `__main__`, dict keys read from external payloads). Existing committed string literals are not retroactively rewritten.

`AVOID docstrings WHEN purpose_evident_from_name_and_parameters`: a docstring carries the *why* the name cannot carry. `retry_delay(attempt, base) -> float` needs no docstring. Do write one for a non-obvious constraint, a unit, a side effect, or a reference to an outside rule. Do not restate the signature. Keep a module docstring when it explains the module's purpose, not its contents.

Other rules express KISS over deduplication when they conflict. The list also includes: avoidance of speculative abstractions. `pathlib.Path` over `os.path` for path manipulation. Functions by default, unless shared mutable state or polymorphism calls for classes. A ban on bare `except:`.

## Limits

- Static grammar validation cannot prove a named condition is meaningful or that two differently-worded rules are logically equivalent.
- The validator detects exact duplicates and direct contradictions for identical scope/target/condition signatures. Broader semantic overlaps still need model or human review.
