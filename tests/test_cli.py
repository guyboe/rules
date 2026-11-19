"""Tests for bin/rules."""

import subprocess

import pytest

from conftest import ROOT, run


class TestWake:
    def test_wake_prints_policy(self, store):
        result = run(store, "wake")
        assert result.returncode == 0
        assert "[general]" in result.stdout
        assert "PREFER simple_design OVER deduplication" in result.stdout

    def test_wake_prints_version_line(self, store):
        result = run(store, "wake")
        assert result.stdout.startswith("RULES v1.0 @ ")
        assert "(clean)" in result.stdout.splitlines()[0]

    def test_wake_prints_pointer(self, store):
        result = run(store, "wake")
        assert "rules get rules.tx" in result.stdout
        assert "rules get semantics.md" in result.stdout

    def test_wake_prints_glossary(self, store):
        result = run(store, "wake")
        assert "abbreviations — " in result.stdout
        assert result.stdout.index("[general]") < result.stdout.index(
            "abbreviations — "
        )

    def test_wake_without_git_repository(self, store):
        result = run(store, "wake")
        assert result.returncode == 0
        assert not result.stderr.strip()

    def test_wake_missing_store(self, tmp_path):
        result = run(tmp_path / "absent", "wake")
        assert result.returncode == 2
        assert "not installed" in result.stderr
        assert "rules init" in result.stderr

    def test_wake_reports_dirty_store(self, store):
        git = ["git", "-C", str(store)]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run(
            [
                *git,
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@t",
                "commit",
                "-qm",
                "one",
            ],
            check=True,
        )
        (store / "python.rules").write_text("[general]\nAVOID x\n", encoding="utf-8")
        result = run(store, "wake")
        assert "(dirty)" in result.stdout.splitlines()[0]


class TestVersion:
    def test_version_without_git(self, store):
        result = run(store, "version")
        assert result.returncode == 0
        assert "unknown" in result.stdout


class TestShow:
    def test_show_lists_scopes(self, store):
        result = run(store, "show")
        assert result.returncode == 0
        assert "[general]" in result.stdout
        assert "[types]" in result.stdout

    def test_show_scope_prints_policies(self, store):
        result = run(store, "show", "filesystem")
        assert "PREFER pathlib.Path OVER os.path" in result.stdout
        assert "[general]" not in result.stdout

    def test_show_target_prints_matching_line(self, store):
        result = run(store, "show", "getattr_or_dict_get")
        assert "FORBID getattr_or_dict_get" in result.stdout

    def test_show_scope_ignores_glossary(self, store):
        result = run(store, "show", "documentation")
        assert result.returncode == 0
        assert "—" not in result.stdout
        assert "AVOID docstrings" in result.stdout

    def test_show_target_ignores_glossary(self, store):
        result = run(store, "show", "getattr_or_dict_get")
        assert result.returncode == 0
        assert result.stdout.strip().splitlines() == [
            "FORBID getattr_or_dict_get WHEN "
            "accessing_declared_pydantic_or_dataclass_fields"
        ]

    def test_show_unknown_topic(self, store):
        result = run(store, "show", "nonsense")
        assert result.returncode == 2
        assert "[general]" in result.stderr


class TestGet:
    def test_get_grammar(self, store):
        result = run(store, "get", "rules.tx")
        assert result.returncode == 0
        assert "Model:" in result.stdout

    def test_get_embed_file(self, store):
        result = run(store, "get", "agents/opencode/embed.md")
        assert result.returncode == 0
        assert result.stdout == (store / "agents/opencode/embed.md").read_text(
            encoding="utf-8"
        )

    def test_get_add_command_file(self, store):
        result = run(store, "get", "agents/opencode/rules.add.md")
        assert result.returncode == 0
        assert "Stage 1" in result.stdout

    def test_get_glossary_file(self, store):
        result = run(store, "get", "python.glossary")
        assert result.returncode == 0
        assert "simple_design — " in result.stdout

    def test_get_glossary_grammar(self, store):
        result = run(store, "get", "glossary.tx")
        assert result.returncode == 0
        assert "GlossaryModel:" in result.stdout

    def test_get_unknown_file(self, store):
        result = run(store, "get", "nope.md")
        assert result.returncode == 2
        assert "semantics.md" in result.stderr


class TestUsage:
    def test_usage_lists_commands(self):
        result = run(None, "nonsense")
        assert result.returncode == 2
        assert "wake" in result.stdout
        assert "validate" in result.stdout

    def test_no_arguments_prints_usage(self):
        result = run(None)
        assert result.returncode == 0
        assert "rules wake" in result.stdout


class TestPull:
    def test_pull_without_remote_reports_failure(self, store):
        result = run(store, "pull")
        assert result.returncode == 1
        assert "pull" in result.stderr.lower()

    def test_pull_failure_stays_quiet_inside_wake(self, store):
        result = run(store, "wake")
        assert result.returncode == 0
        assert "pull failed" not in result.stderr


class TestInit:
    def test_init_prints_install_block(self, store):
        result = run(store, "init")
        assert result.returncode == 0
        assert "ln -s" in result.stdout
        assert "rules wake" in result.stdout
        assert "AGENTS.md" in result.stdout

    def test_init_prints_opencode_embed_block(self, store):
        result = run(store, "init")
        assert result.returncode == 0
        assert "instructions" in result.stdout
        assert f"{store}/agents/opencode/embed.md" in result.stdout
        assert "commands/rules" in result.stdout
        assert f"{store}/agents/opencode/rules.add.md" in result.stdout


class TestPrompt:
    def test_prompt_prints_agents_block(self, store):
        result = run(store, "prompt")
        assert result.returncode == 0
        assert result.stdout.startswith("# Rules\n\n")
        assert result.stdout == (store / "agents/opencode/embed.md").read_text(
            encoding="utf-8"
        )
        assert "rules wake" in result.stdout
        assert "rules init" in result.stdout

    def test_prompt_mentions_glossary(self, store):
        result = run(store, "prompt")
        assert "python.glossary" in result.stdout
        assert "alphabetical" in result.stdout

    def test_prompt_missing_embed_file(self, tmp_path):
        target = tmp_path / "rules-store"
        target.mkdir()
        (target / "python.rules").write_text("[general]\n", encoding="utf-8")
        (target / "agents").mkdir()
        (target / "agents/opencode").mkdir()
        (target / "agents/opencode/rules.add.md").write_text(
            "---\ndescription: probe\n---\nx\n", encoding="utf-8"
        )
        result = run(target, "prompt")
        assert result.returncode == 2
        assert "embed.md is missing" in result.stderr

    def test_prompt_block_is_part_of_init_output(self, store):
        prompt = run(store, "prompt")
        init = run(store, "init")
        assert prompt.returncode == 0
        assert prompt.stdout.strip() in init.stdout


class TestValidate:
    @pytest.mark.manual
    def test_validate_accepts_shipped_policy(self):
        result = run(None, "validate")
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout

    @pytest.mark.manual
    def test_validate_rejects_broken_policy(self, store):
        (store / "python.rules").write_text("[a]\nPREFER x\n", encoding="utf-8")
        result = run(store, "validate")
        assert result.returncode == 1
        assert "PREFER requires OVER" in result.stderr
