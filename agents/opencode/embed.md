# Rules

Python implementation choices are governed by the Rules store. Run
`rules wake` at session start; it prints the active policy and version.
For the grammar use `rules get rules.tx`, for symbol explanations
`rules get python.glossary`, for interpretation `rules get semantics.md`.
Never copy policy files into this repository.

- Follow the active policy when writing or refactoring code.
- Edit the policy only when the user explicitly requests a persistent rule
  change, and only in the store. Never persist incidental coding
  discussion. Keep one rule per line. Reuse existing scopes and targets.
  Keep python.glossary in sync and alphabetical. Replace superseded rules
  instead of appending contradictions.
- After a rule change run `rules validate`.
- If `rules` is missing, say so and stop. Do not write code without the
  policy. `rules init` prints the install block.
