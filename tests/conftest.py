"""Shared pytest fixtures + path setup for the LAZARUS oracle tests.

Adds the repo root to sys.path so `import src.differential_oracle` works no
matter where pytest is invoked from, and exposes a `cobc_available` marker so
the subprocess-backed tests skip cleanly on machines without GnuCOBOL.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
# Put the repo's src/ first so `import differential_oracle` resolves to the
# module under test (a site-packages 'src' package would otherwise shadow it).
for p in (str(SRC_DIR), str(REPO_ROOT)):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


def have_cobc() -> bool:
    return shutil.which("cobc") is not None


requires_cobc = pytest.mark.skipif(
    not have_cobc(),
    reason="GnuCOBOL (cobc) not installed; oracle compile/run path skipped",
)
