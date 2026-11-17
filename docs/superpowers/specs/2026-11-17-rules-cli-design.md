# Rules CLI — design

## Intent

`rules/` (a grammar, a policy file, a contract, and a validator) is copied
into three repositories. The copies drifted: one lacks the PEP 723 header
and the StrEnum policy, another carries a local rule. The policies guide
an LLM agent, not the program: no project imports or executes them. Copying
them into every repository therefore buys nothing and costs synchronization
work that the single maintainer forgets.

The store moves out of the projects. One command gives the agent the active
policy on any machine. Projects keep one paragraph in `AGENTS.md`.

## Goals

- One canonical store, outside every project.
- One command at session start prints the active policy and its version.
- No project files, no submodule, no subtree, no synchronization commits.
- Works on any machine after a one-time install.
- Validation runs in the store, where edits happen.

## Non-goals

- Per-project rule layers. Dropped by the user: the policy is identical
  everywhere.
- Automatic language selection (`python.rules` is the only policy now).
- Rules visible in a project's history or in a project diff.

## Anti-goals

- Silent fallback when the store is missing. The agent must see a failure.
- A hard network dependency at session start. Wake works offline.

## Constraints

- Python 3.13, standard library only. Same shape as `~/.optmem/memo`.
- `validate.py` keeps its PEP 723 header. `uv run --no-project` builds its
  environment; `textx` is not a project dependency.
- The store is a git repository. The remote is added by the user; the
  machine has no `gh` CLI.

## Decisions

| Decision | Value | Why |
| --- | --- | --- |
| Store location | `~/development/rules` | Visible next to the projects, its own git repo |
| Override | `RULES_DIR` environment variable | Mirrors OptMem's `MEMORY_DIR`; tests use it |
| Default resolution | directory of the resolved script | A symlink works from any working directory |
| Command name | `rules` | No collision with an existing binary |
| Install | symlink in `~/.local/bin` | `~/.local/bin` is on `PATH` |
| Wake content | policy lines plus one version line | About 1 KB: cheap, complete |
| Pull at wake | best effort, 5 s timeout, silent on failure | Offline must not break the session |
| Local rules | none | The `[documentation]` rule from `adviser` becomes shared |

## Store layout

```
~/development/rules/
  bin/rules            # the CLI (stdlib only)
  python.rules         # the active policy
  rules.tx             # grammar for the policy language
  semantics.md         # interpretation and editing protocol
  validate.py          # PEP 723 validator (textX)
  tests/test_cli.py    # CLI tests
  tests/test_validate.py
  README.md
  .pre-commit-config.yaml
```

## Command surface

| Command | Behavior |
| --- | --- |
| `rules wake` | Pull best effort, print a version line, print `python.rules`, print one pointer line to `rules.tx` and `semantics.md` |
| `rules show [TOPIC]` | Without argument: list scopes with their line counts. With a scope or a target name: print the matching policy lines |
| `rules get FILE` | Print a store file: `python.rules`, `rules.tx`, `semantics.md` |
| `rules validate` | Run `validate.py` on `python.rules` through `uv run --no-project` |
| `rules version` | Print the store commit and whether the work tree is dirty |
| `rules pull` | `git pull --ff-only` in the store |
| `rules edit` | Open the store in `$EDITOR` |
| `rules init` | Print the install block: symlink command, `AGENTS.md` paragraph, hook commands |

## Wire format of `wake`

```
RULES v1.0 @ 1a2b3c4 (clean)
Grammar: rules get rules.tx. Contract: rules get semantics.md.

[general]
PREFER simple_design OVER deduplication WHEN principles_conflict
...
```

The second line is the pointer the agent follows only when it needs the
grammar or the editing protocol. The rest is the policy, verbatim.

## Failure modes

| Condition | Behavior |
| --- | --- |
| Store missing or `python.rules` absent | Exit 2, `rules not installed: run rules init` |
| No git remote, or offline | Wake prints the policy and the local version; no error |
| Store work tree dirty | Version line says `dirty` instead of `clean` |
| Unknown scope or target in `show` | Exit 2, list available scopes |
| Unknown file in `get` | Exit 2, list available files |
| `uv` missing in `validate` | Exit 2, say `uv is required for validate` |

## Consumer block (`AGENTS.md`)

`rules init` prints the block. Projects paste it unchanged.

```
## Rules
Python implementation choices are governed by the Rules store. Run
`rules wake` at session start; it prints the active policy and version.
For the grammar use `rules get rules.tx`, for interpretation
`rules get semantics.md`. Never copy policy files into this repository.

- Follow the active policy when writing or refactoring code.
- Edit the policy only when the user explicitly requests a persistent rule
  change, and only in the store. Never persist incidental coding
  discussion. Keep one rule per line. Reuse existing scopes and targets.
  Replace superseded rules instead of appending contradictions.
- After a rule change run `rules validate`.
- If `rules` is missing, say so and stop. Do not write code without the
  policy. `rules init` prints the install block.
```

## What is left to the builder

- Exact wording of the `init` block.
- Whether `README.md` needs more than the command table.
- The order of the migration steps in the three projects.
