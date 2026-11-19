# Rule indexes (v1.1) — design

**Intent.** Every policy line gets a permanent, citable identifier. Review feedback
becomes "you violated EX0001", agents cite rules by ID, `rules show <ID>` finds a
rule fast, and a superseded rule keeps its history addressable.

**Approaches.**
1. *IDs stored in the rule line, grammar-required.* Permanent, grammatically
   enforced, `show` finds them for free (word search already matches the ID).
   Chosen.
2. *Optional IDs.* Softer migration, but no guarantee every rule is addressable;
   rejected — the point of the feature is exactly that guarantee.
3. *On-the-fly numbering in CLI output.* No file or grammar change, but IDs drift
   after edits, so references die. Rejected.

**Decisions (all user-made):**
- ID = two uppercase letters (first two letters of the scope, capitalized) + four
  digits, e.g. `GE0001`.
- IDs are mandatory in the grammar from v1.1; a rule without an ID is invalid.
- IDs are never renumbered. Deleting a rule leaves a gap; the retired ID keeps
  pointing at "no active rule with this ID". A new rule takes max+1 in its letter
  pool.
- Validator adds two checks: ID prefix equals the first two letters of the
  enclosing scope (uppercase), and IDs are unique across the file.

**Migration.** One commit assigns IDs to all 17 existing rules. Today's scopes
(GE FI AR EX MO NA TY DO PO) have distinct two-letter prefixes; a future prefix
collision (TE for [tests] and [testing]) shares one pool, which uniqueness
handles.

**Language bump:** v1.0 → v1.1 everywhere the version is printed
(`bin/rules` LANGUAGE, headers of `rules.tx`, `python.rules`, `semantics.md`).
