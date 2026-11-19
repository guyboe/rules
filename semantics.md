# Rules v1.1 — LLM contract

**Purpose:** guide Python implementation choices, not validate Python source code.
Read `rules.tx` as the definitive syntax. Read `python.rules` as the active policy. Read `python.glossary` for symbol explanations.

## Interpretation

- Every policy is ONE physical line inside the preceding `[scope]`. No line continuation, no trailing `;`, no quoted strings, no inline comments.
- Every policy line starts with its ID: two uppercase letters (the first two letters of the scope) then four digits, e.g. `EX0002`. Cite rules by ID, as in `rules show EX0002`.
- `USE X`: X is required when applicable. `PREFER X OVER Y`: choose X rather than Y by default. `AVOID X`: avoid X by default. `FORBID X`: do not use X in the applicable context.
- `WHEN C`: apply the policy only if C is true. `UNLESS C`: do not apply it if C is true. Both may coexist. Effective applicability is `WHEN and not UNLESS`.
- A condition is a sequence of named predicates joined by `AND`/`OR`. `AND` binds tighter than `OR`. Parentheses and negation are intentionally unsupported. Split complicated rules into simple independent policies.
- Names like `stateless_leaf` are *semantic predicates* interpreted from the coding task, not built-in executable expressions. Avoid opaque abbreviations. The grammar guarantees syntax, not universal semantic truth.
- Scopes are topic labels, not a formal hierarchy. Use the most appropriate scope.
- Every target, alternative, and condition name used by a policy has exactly one explanation line in `python.glossary`, shaped `name — explanation`. The glossary is a separate file, parsed by `glossary.tx`, and holds no policies. Its entries are unique and kept in alphabetical order. `validate.py` rejects duplicates and disorder.
- Prefer a narrower applicable instruction over a generic preference. Do not resolve irreconcilable mandatory/forbidden conflicts by guessing. Ask for clarification.
- `USE`/`FORBID` are strict instructions, `PREFER`/`AVOID` are defaults. Do not reinterpret a preference as an absolute constraint.

## Editing protocol

When the user **explicitly requests a persistent rule change**:
1. Read the policy (`python.rules`) and this file. Do not automatically persist incidental coding discussion.
2. Express exactly the requested preference using `USE`, `PREFER`, `AVOID`, `FORBID`, optionally `OVER`, `WHEN`, `UNLESS`. Keep one rule per line.
3. Reuse existing scopes, targets, and conditions when the existing ones are equivalent. Avoid duplicates. Preserve all unrelated policies.
4. Assign the policy its ID once and never renumber: deleting a policy leaves its ID retired; a new policy takes the next free number in its letter pool (`max + 1`), even after gaps.
5. Keep `python.glossary` in sync: every target, alternative, and condition name needs exactly one `name — explanation` line in `python.glossary`. Add entries for new names, rename them with their symbol, and delete entries no policy uses. Keep the entries in alphabetical order. `validate.py` rejects duplicates and disorder.
6. Replace superseded rules instead of appending contradictory copies. A superseded policy keeps its old ID retired; the replacement takes a new ID. Do not silently introduce new exceptions or broader prohibitions.
7. If a significant ambiguity cannot be safely resolved, ask rather than inventing meaning.
8. Keep a final newline. Run `rules validate` before committing.

## Examples and intent

Per-symbol explanations live in `python.glossary`: one `name — explanation` line for every target, alternative, and condition used by a policy. Read them there. This contract keeps only the generic reading rules.

## Limits

- Static grammar validation cannot prove a named condition is meaningful or that two differently-worded rules are logically equivalent.
- The validator detects exact duplicates and direct contradictions for identical scope/target/condition signatures. Broader semantic overlaps still need model or human review.
