"""Pytest fixtures + path setup so the flat inner-package modules import.

Adds the inner `helthi/` package dir to sys.path (mirrors pyproject's
[tool.pytest.ini_options] pythonpath) so `import db`, `import time_align`, etc.
work when running pytest from anywhere.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT / "helthi"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

for p in (str(PKG_DIR),):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture()
def db(tmp_path):
    """A fresh in-schema SQLite connection backed by a temp file."""
    from db import init_db

    conn = init_db(tmp_path / "test.db")
    yield conn
    conn.close()


@pytest.fixture()
def whoop_sample():
    return json.loads((FIXTURES / "whoop_sample.json").read_text())


@pytest.fixture()
def home_tz():
    return "Asia/Dubai"
