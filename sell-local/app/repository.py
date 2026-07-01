"""Data access. All public reads funnel through db.PUBLIC_PREDICATE.

Kept deliberately thin (raw parameterised SQL, no ORM) per the blueprint's
"boring tech" and SQLite-scale constraints.
"""
import re
import sqlite3
from typing import List, Optional

from .db import PUBLIC_PREDICATE, public_params


# --- communities ------------------------------------------------------------
def list_active_communities(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM community WHERE is_active = 1 ORDER BY name COLLATE NOCASE"
    ).fetchall()


def get_community_by_slug(conn: sqlite3.Connection, slug: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM community WHERE slug = :slug AND is_active = 1",
        {"slug": slug},
    ).fetchone()


# --- listings ---------------------------------------------------------------
def list_public_listings(
    conn: sqlite3.Connection,
    community_id: int,
    limit: int,
    offset: int = 0,
) -> List[sqlite3.Row]:
    """Approved, unexpired listings for a community, newest first."""
    sql = (
        "SELECT * FROM listing "
        f"WHERE {PUBLIC_PREDICATE} AND community_id = :cid "
        "ORDER BY created_at DESC, id DESC "
        "LIMIT :limit OFFSET :offset"
    )
    params = public_params(cid=community_id, limit=limit, offset=offset)
    return conn.execute(sql, params).fetchall()


def count_public_listings(conn: sqlite3.Connection, community_id: int) -> int:
    sql = (
        "SELECT COUNT(*) AS n FROM listing "
        f"WHERE {PUBLIC_PREDICATE} AND community_id = :cid"
    )
    return conn.execute(sql, public_params(cid=community_id)).fetchone()["n"]


def get_public_listing(conn: sqlite3.Connection, listing_id: int) -> Optional[sqlite3.Row]:
    """A single listing, only if it passes the public predicate."""
    sql = f"SELECT * FROM listing WHERE {PUBLIC_PREDICATE} AND id = :id"
    return conn.execute(sql, public_params(id=listing_id)).fetchone()


# --- FTS5 search ------------------------------------------------------------
_FTS_TOKEN = re.compile(r"[A-Za-z0-9؀-ۿ]+")  # latin, digits, Arabic


def build_fts_query(raw: str) -> Optional[str]:
    """Turn untrusted user input into a safe FTS5 MATCH string.

    We never pass raw input to MATCH (FTS5 has its own query syntax that can
    error or behave oddly). Extract word tokens and AND them together with a
    prefix on the final token for search-as-you-type. Returns None if nothing
    searchable remains.
    """
    tokens = _FTS_TOKEN.findall(raw or "")
    if not tokens:
        return None
    quoted = [f'"{t}"' for t in tokens[:-1]]
    quoted.append(f'"{tokens[-1]}"*')  # prefix match on last token
    return " AND ".join(quoted)


def search_public_listings(
    conn: sqlite3.Connection,
    community_id: int,
    query: str,
    limit: int,
    offset: int = 0,
) -> List[sqlite3.Row]:
    """FTS5 search over title+description within a community, public predicate applied."""
    match = build_fts_query(query)
    if match is None:
        return []
    sql = (
        "SELECT l.* FROM listing l "
        "JOIN listing_fts f ON f.rowid = l.id "
        f"WHERE listing_fts MATCH :match AND {PUBLIC_PREDICATE} AND l.community_id = :cid "
        "ORDER BY l.created_at DESC, l.id DESC "
        "LIMIT :limit OFFSET :offset"
    )
    params = public_params(match=match, cid=community_id, limit=limit, offset=offset)
    return conn.execute(sql, params).fetchall()
