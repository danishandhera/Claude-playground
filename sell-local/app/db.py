"""SQLite connection helpers + the single public-read predicate.

Every public listing query MUST go through PUBLIC_PREDICATE / public_params so the
rule `status='approved' AND expires_at > now` lives in exactly one place
(Architecture §3 "single source of truth").
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import DB_PATH

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# --- The one public-read predicate ------------------------------------------
# Callers append their own scoping (community_id, FTS id set) and ORDER BY.
PUBLIC_PREDICATE = "status = 'approved' AND expires_at > :now"


def utc_now_iso() -> str:
    """Current UTC time as ISO-8601, matching how timestamps are stored."""
    return datetime.now(timezone.utc).isoformat()


def public_params(**extra) -> dict:
    """Bind params for the public predicate; merge in any extra query params."""
    params = {"now": utc_now_iso()}
    params.update(extra)
    return params


def connect() -> sqlite3.Connection:
    """Open a connection with WAL, foreign keys, and Row access."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables, indexes, FTS table, and triggers (idempotent)."""
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
