# Design: embed the policy in OpenCode, add the /rules-add command

Date: 2026-11-19
Status: approved

## Problem

Opening a session has no policy until the agent runs `rules wake`, and adding a
new policy requires a hand-written prompt each time.

## Goals

1. OpenCode receives the policy paragraph in every session without file copying.
2. `/rules/add <request>` formulates a policy in two supervised stages.
3. The binary only prints. It never edits OpenCode configuration.

## Non-goals

- No Claude Code, Codex, or other-host embedding (later, same pattern).
- No similarity heuristic beyond the model reading the full glossary.

## Design

### Store: `opencode.md`

New file holding the paragraph that `rules prompt` prints today.

- `AGENTS_BLOCK` is deleted from `bin/rules`. `opencode.md` is the single
  source of the paragraph.
- `cmd_prompt` reads `opencode.md` and prints it. A missing file is an error:
  `store is incomplete: opencode.md is missing` and exit code 2. No silent
  fallback (README line: a missing store is an error, never a silent fallback).
- `cmd_init` reads the same file for the AGENTS.md paragraph and fails the
  same way. The test `test_prompt_block_is_part_of_init_output` compares the
  two outputs, so drift between the two callers is impossible by construction.
- `SERVED` in `bin/rules` gains `"opencode.md"`, so `rules get opencode.md` works.
- `wake` is unchanged. The runtime contract stays policy plus glossary.

### Store: `opencode.add.md`

New file holding the command template for the policy-add flow. `SERVED` gains
it, so `rules get opencode.add.md` works and the installed command is a
symlink to the store copy. Template content is fixed in this spec and
quoted below. Store paths inside the template are concrete: reads go through
`rules get` (works under `RULES_DIR`), writes name the store files directly
under `~/development/rules`, matching the wiring section. An install with a
different `RULES_DIR` edits the store-path line in the template once.

Template file `opencode.add.md`:

```md
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
```

### Binary: print-only embed instructions

`rules init` prints a new block directly after the AGENTS.md paragraph block.
Both install targets are manual commands the user runs. Nothing is written
outside the store.

```
Embed in OpenCode (https://opencode.ai/docs/instructions):

In ~/.config/opencode/opencode.json add:

  "instructions": ["<store>/opencode.md"]

Install the /rules-add command:

  mkdir -p ~/.config/opencode/commands/rules
  ln -sfn <store>/opencode.add.md ~/.config/opencode/commands/rules/add.md
```

`<store>` is the `store_path()` output. With the default store this prints
`~/development/rules`.

### OpenCode wiring (manual, once)

The user adds this to the global `opencode.json`:

```json
"instructions": ["~/development/rules/opencode.md"]
```

The user runs the two commands from the init block to install the command
symlink. OpenCode loads the instruction file in every session and reloads it
after a change. OpenCode reloads command files without a restart.

### Files touched

Store and repo:

- new `opencode.md` (the paragraph text, current `AGENTS_BLOCK` content)
- new `opencode.add.md` (the template quoted above)
- `bin/rules`: `SERVED` gains two names. Delete `AGENTS_BLOCK`.
  `cmd_prompt` and `cmd_init` read `opencode.md`. `cmd_init` prints the new
  block. The docstring file list for `rules get` gains `opencode.md`,
  `opencode.add.md`, and `validate.py`. Today it omits `validate.py`.
- `README.md`: Store table gains the two files. The `rules get <file>` row
  already reads "print `python.rules`, `python.glossary`, ..." and gains the
  two names. Add a project is unchanged.
- `tests/conftest.py`: the `store` fixture copies the two new files
- `tests/test_cli.py`: prompt and init read from the store copy. New tests
  cover a missing `opencode.md` (exit 2) and the new init block.

Host files (outside the repo, manual):

- `~/.config/opencode/opencode.json`: one `instructions` entry
- `~/.config/opencode/commands/rules/add.md`: symlink to the store copy

## Testing

- Store: `rules validate` and the pytest suite pass.
- CLI: `rules get opencode.md` and `rules get opencode.add.md` print the
  store files. `rules prompt` with a store missing `opencode.md` exits 2.
- Manual (user run): `/rules/add` in a fresh OpenCode session.

## Alternatives rejected

- Binary edits `opencode.json` or creates the command symlink. Rejected
  because the store never mutates host configuration; init prints the exact
  commands.
- Skill instead of command. Rejected because the invocation is explicit, and
  the protocol already lives in `semantics.md`.
- Keep `AGENTS_BLOCK` as a fallback constant. Rejected because two copies of
  the paragraph drift.
