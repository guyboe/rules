# Rules

The implementation-policy store for AI agents.

The policy guides the agent, not the program. No project imports or
executes it, so no project stores a copy. The agent reads it with one
command at the start of a session.

## Store

| File | Purpose |
| --- | --- |
| `python.rules` | The active policy. One rule per line. |
| `python.glossary` | One `name — explanation` line per symbol used by the policy, alphabetical. |
| `rules.tx` | The grammar of the policy language. |
| `glossary.tx` | The grammar of the glossary language. |
| `semantics.md` | How to read a rule, and the editing protocol. |
| `validate.py` | Syntax and consistency check (textX, PEP 723). |
| `agents/opencode/embed.md` | The paragraph for the OpenCode `instructions` entry. |
| `agents/opencode/rules.add.md` | The template of the OpenCode `/rules/add` command. |
| `agents/opencode/rules.check.md` | The template of the OpenCode `/rules/check` command: a policy pass over a repository or files, run before every commit. |
| `bin/rules` | The command line tool. |

## Commands

| Command | Result |
| --- | --- |
| `rules wake` | Pull best effort, print the version, print the policy and glossary |
| `rules show` | List scopes with their policy counts |
| `rules show <scope>` | Print the policies of one scope |
| `rules show <target>` | Print the policies that name one target |
| `rules show <ID>` | Print the policy with that ID, e.g. `EX0002` |
| `rules get <file>` | Print `python.rules`, `python.glossary`, `rules.tx`, `glossary.tx`, `semantics.md`, `validate.py`, `agents/opencode/embed.md`, `agents/opencode/rules.add.md` |
| `rules validate` | Check `python.rules` and `python.glossary` through `uv run --no-project` |
| `rules version` | Print the store commit and `clean` or `dirty` |
| `rules pull` | Update the store: `git pull --ff-only` |
| `rules edit` | Open the store in `$EDITOR` |
| `rules prompt` | Print the paragraph for a project's `AGENTS.md` |
| `rules check` | Print the policy-check prompt (the `/rules/check` command body) |
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

Install in OpenCode:

```bash
mkdir -p ~/.config/opencode/commands/rules
ln -sfn ~/development/rules/agents/opencode/rules.add.md ~/.config/opencode/commands/rules/add.md
ln -sfn ~/development/rules/agents/opencode/rules.check.md ~/.config/opencode/commands/rules/check.md
```

Then add `"instructions": ["~/development/rules/agents/opencode/embed.md"]` to
`~/.config/opencode/opencode.json`. `rules init` prints both blocks with the
expanded store path.

## Add a project

Add the paragraph that `rules init` prints to the project's `AGENTS.md`.
Do not copy policy files into the project.

## Change a rule

1. `rules edit`
2. Change `python.rules`. Keep one physical line per policy. Each policy line
   starts with its permanent ID — the scope's first two letters capitalized plus
   the next free number (`max + 1` in the two-letter pool); never renumber.
   Keep `python.glossary` in sync with the symbols the policies use, in
   alphabetical order, one `name — explanation` line per symbol.
3. `rules validate`
4. Commit the store.

The projects need no change. They see the new policy at the next
`rules wake`.

## Check before a commit

The policy is enforced by an agent pass, not by an external linter. In a
project whose policy is the Rules store, run the check before every commit
(`rules check` prints the same prompt for a bare agent):

- OpenCode: run `/rules/check` with the repository, or a narrower target
  such as a directory or files.
- Bare agent: run `rules check` and follow the printed prompt over the
  same target.

`validate.py` stays a store-internal check of the policy and glossary
syntax only; it never scans project code.

## Tests

```bash
uv run --no-project --with pytest pytest tests -q
```

Tests marked `manual` run `uv` and need the textX package. The first run
downloads it once.
