"""SQLite connection, schema application, and upsert helpers.

Mirrors Leo-Health-Core's db/ingest.py pattern: stdlib sqlite3 + plain SQL, no
ORM. All ingest is idempotent -- upserts key on the table's primary/natural key.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

PACKAGE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = PACKAGE_DIR / "schema.sql"


def now_utc_iso() -> str:
    """Current time as ISO-8601 UTC text (seconds precision, 'Z' suffix)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def connect(db_path: Path) -> sqlite3.Connection:
    """Open (creating parent dirs as needed) a SQLite connection with sane pragmas."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def apply_schema(conn: sqlite3.Connection, schema_path: Path = SCHEMA_PATH) -> None:
    """Apply schema.sql. Idempotent (all statements are CREATE ... IF NOT EXISTS)."""
    sql = Path(schema_path).read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def init_db(db_path: Path, schema_path: Path = SCHEMA_PATH) -> sqlite3.Connection:
    """Connect and ensure schema is present. Returns the open connection."""
    conn = connect(db_path)
    apply_schema(conn, schema_path)
    return conn


# --------------------------------------------------------------------------- #
# Upsert helpers
# --------------------------------------------------------------------------- #
def upsert(
    conn: sqlite3.Connection,
    table: str,
    row: Dict[str, Any],
    conflict_keys: Iterable[str],
) -> None:
    """Insert-or-replace `row` into `table`, keyed on `conflict_keys`.

    Uses SQLite's ON CONFLICT ... DO UPDATE so re-ingesting the same source row
    overwrites in place (Whoop can recompute scores days later -- always take the
    newest payload). Column names come from `row` keys and are validated against
    a simple identifier charset to avoid SQL injection via dict keys.
    """
    cols = list(row.keys())
    _validate_identifiers([table, *cols, *conflict_keys])

    placeholders = ", ".join("?" for _ in cols)
    col_list = ", ".join(cols)
    conflict_list = ", ".join(conflict_keys)
    update_cols = [c for c in cols if c not in set(conflict_keys)]
    update_clause = ", ".join(f"{c}=excluded.{c}" for c in update_cols)

    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    if update_cols:
        sql += f" ON CONFLICT({conflict_list}) DO UPDATE SET {update_clause}"
    else:
        sql += f" ON CONFLICT({conflict_list}) DO NOTHING"

    conn.execute(sql, [row[c] for c in cols])


def _validate_identifiers(names: Iterable[str]) -> None:
    for n in names:
        if not all(ch.isalnum() or ch == "_" for ch in n):
            raise ValueError(f"Invalid SQL identifier: {n!r}")


# --------------------------------------------------------------------------- #
# ingest_run bookkeeping
# --------------------------------------------------------------------------- #
def start_ingest_run(conn: sqlite3.Connection, source: str) -> int:
    """Record the start of an ingest run; return its row id."""
    cur = conn.execute(
        "INSERT INTO ingest_run (source, started_at, status) VALUES (?, ?, 'running')",
        (source, now_utc_iso()),
    )
    conn.commit()
    return cur.lastrowid


def finish_ingest_run(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    rows_upserted: int = 0,
    cursor: Optional[str] = None,
    note: Optional[str] = None,
) -> None:
    """Mark an ingest run finished with status/counters."""
    conn.execute(
        "UPDATE ingest_run SET finished_at=?, status=?, rows_upserted=?, cursor=?, "
        "note=? WHERE id=?",
        (now_utc_iso(), status, rows_upserted, cursor, note, run_id),
    )
    conn.commit()


def last_cursor(conn: sqlite3.Connection, source: str) -> Optional[str]:
    """Latest successful watermark cursor for a source, or None if never synced."""
    row = conn.execute(
        "SELECT cursor FROM ingest_run WHERE source=? AND status IN ('ok','partial') "
        "AND cursor IS NOT NULL ORDER BY id DESC LIMIT 1",
        (source,),
    ).fetchone()
    return row["cursor"] if row else None
