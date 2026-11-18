"""Shared fixtures for the CLI tests."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "rules"


def pytest_configure(config):
    config.addinivalue_line("markers", "manual: needs uv and the network")


@pytest.fixture
def store(tmp_path: Path) -> Path:
    target = tmp_path / "rules-store"
    target.mkdir()
    for name in (
        "python.rules",
        "python.glossary",
        "rules.tx",
        "glossary.tx",
        "semantics.md",
        "validate.py",
    ):
        shutil.copy(ROOT / name, target / name)
    return target


def run(store: Path | None, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if store is not None:
        env["RULES_DIR"] = str(store)
    return subprocess.run(
        [str(CLI), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=60,
    )
