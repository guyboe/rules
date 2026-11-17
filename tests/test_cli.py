"""Tests for bin/rules."""

import subprocess

import pytest

from conftest import run


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

    def test_show_unknown_topic(self, store):
        result = run(store, "show", "nonsense")
        assert result.returncode == 2
        assert "[general]" in result.stderr


class TestGet:
    def test_get_grammar(self, store):
        result = run(store, "get", "rules.tx")
        assert result.returncode == 0
        assert "Model:" in result.stdout

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
