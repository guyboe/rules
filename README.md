# Rules

The implementation-policy store for AI agents.

The policy guides the agent, not the program. No project imports or
executes it, so no project stores a copy. The agent reads it with one
command at the start of a session.

## Store

| File | Purpose |
| --- | --- |
| `python.rules` | The active policy. One rule per line. |
| `rules.tx` | The grammar of the policy language. |
| `semantics.md` | How to read a rule, and the editing protocol. |
| `validate.py` | Syntax and consistency check (textX, PEP 723). |
| `bin/rules` | The command line tool. |

## Commands

| Command | Result |
| --- | --- |
| `rules wake` | Pull best effort, print the version, print the policy |
| `rules show` | List scopes with their policy counts |
| `rules show <scope>` | Print the policies of one scope |
| `rules show <target>` | Print the policies that name one target |
| `rules get <file>` | Print `python.rules`, `rules.tx`, `semantics.md`, `validate.py` |
| `rules validate` | Validate `python.rules` through `uv run --no-project` |
| `rules version` | Print the store commit and `clean` or `dirty` |
| `rules pull` | Update the store: `git pull --ff-only` |
| `rules edit` | Open the store in `$EDITOR` |
| `rules init` | Print the install block for a new machine or project |

`wake` works offline. A failed pull is silent inside `wake` and reported
by `rules pull`. A missing store is an error, never a silent fallback.

## Install on a machine

```bash
git clone <url> ~/development/rules
ln -sfn ~/development/rules/bin/rules ~/.local/bin/rules
rules validate
git -C ~/development/rules config core.hooksPath .githooks
```

The last command installs the commit hook. It runs `rules validate`
before every commit in the store, so a broken policy never lands.

The default store path is `~/development/rules`, resolved from the
symlink. Set `RULES_DIR` to use another path.

## Add a project

Add the paragraph that `rules init` prints to the project's `AGENTS.md`.
Do not copy policy files into the project.

## Change a rule

1. `rules edit`
2. Change `python.rules`. Keep one physical line per policy.
3. `rules validate`
4. Commit the store.

The projects need no change. They see the new policy at the next
`rules wake`.

## Tests

```bash
uv run --no-project --with pytest pytest tests -q
```

Tests marked `manual` run `uv` and need the textX package. The first run
downloads it once.
