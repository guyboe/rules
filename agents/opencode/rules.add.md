---
description: Add a policy to the rules store. Propose first. Apply after approval.
---

Add the policy described below to the Rules store. Read the store files with
`rules get`. Write to the store at ~/development/rules (or $RULES_DIR when
set).

Policy request: $ARGUMENTS

If the policy request is empty, ask what policy to add. Then continue.

Stage 1 (propose, read-only, one message):
1. Run `rules get semantics.md`, `rules get rules.tx`, `rules get
   python.rules`, and `rules get python.glossary`. Read every result in full.
2. Formulate ONE rules-language line for the request. Use the operators USE,
   PREFER, AVOID, FORBID with the optional OVER, WHEN, UNLESS. Pick the most
   fitting existing scope. Reuse an existing glossary term when it fits.
3. List every existing glossary term close in meaning to each new term. Reuse
   or rename instead of adding a near-duplicate.
4. Present in one message: the rule line with its scope and a one-line
   reason. Then the new glossary lines. Then a Russian translation of the
   rule line and every new glossary line. Then the similarity list, or the
   words "none found".
5. Stop. Make NO edits. Wait for approval.

Stage 2 (apply, only after explicit approval):
6. Add the rule line to python.rules under the proposed scope. Add the new
   glossary lines to python.glossary in alphabetical order. If the request
   supersedes an existing rule, replace that line instead of appending.
7. Run `rules validate`. On failure, fix the presented text and run it again.
   Never commit a failing store. Never bypass the pre-commit hook.
8. Commit the two files with "feat(<scope>): <one-line summary>".
9. Report the commit hash and the validate output.

Never touch unrelated policies. Ask instead of inventing meaning for an
ambiguity. If the store path is wrong, say so instead of guessing.
