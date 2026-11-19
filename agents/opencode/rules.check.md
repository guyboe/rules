---
description: Check a project repository or files against the Rules policy before committing.
---

Check the code below against the Rules policy. Read every store file you
need with `rules get`. Never write to the store from this check; a rule
change goes through the user and `/rules/add`.

Target: $ARGUMENTS

If $ARGUMENTS is empty, check the working tree of the repository in the
current working directory. Then continue.

Stage 1 (gather, read-only):
1. Run `rules wake`. Read every policy line.
2. Run `rules get python.glossary`. A policy applies to a construct only
   when every one of its conditions holds under the glossary reading.
3. A rule applies to new or edited code; existing committed code that a
   rule would rewrite wholesale stays as is. When unsure whether the
   target is new code, ask.

Stage 2 (scan, read-only):
4. For each policy, decide which files it is relevant to. Skip files where
   no policy can apply (generated code, vendored code, binary blobs).
5. Scan the relevant files. When a policy marks one violation of a
   mechanical pattern, search the file for the same pattern and check
   every remaining occurrence before reporting.
6. For every violation record: file, line, the rule ID, and the reason
   the conditions hold. Cite the ID (e.g. `GE0003`).

Stage 3 (report, read-only, one message):
7. Group the findings by rule ID: file and line, the policy line, and the
   reason. FORBID and USE come first, then PREFER and AVOID.
8. If no policy applies to any file, or no condition holds, say so
   explicitly. Never invent findings.
9. Stop. Make NO edits. Wait for the user to choose which findings to fix.

Stage 4 (fix, only after explicit user selection):
10. Fix only the findings the user selected, one at a time, testing after
    each. Apply every remaining occurrence of the same pattern in the
    file in the same pass.
11. Re-run the check on the changed files. Report what changed.

Never touch unrelated files. If a policy is ambiguous in the target
context, report it as a question instead of guessing. If the store path
is wrong, say so instead of guessing.
