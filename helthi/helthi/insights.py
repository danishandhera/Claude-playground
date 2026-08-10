"""Insight computations -- the Backend/Frontend contract (ARCHITECTURE.md §5, §8).

Pure functions over the unified layer (`day`, `session`, `session_hr_zone`). The
FRONTEND (Streamlit dashboard) calls ONLY these functions plus reads the unified
schema; it never touches raw tables. These signatures are STABLE -- frontend can
code against them now while later phases fill the underlying tables.

Return convention
-----------------
Every function returns a list[dict] of records (JSON/DataFrame-friendly:
`pandas.DataFrame(result)` just works). Time-series functions key each record by
`local_day` (ISO date str); session functions key by `session_id`. Records are
sorted ascending by their key. Empty inputs yield an empty list, never an error.

Phase availability
------------------
* IMPLEMENTED NOW (Whoop-only, Phase 1): `recovery_trend`, `sleep_trend`,
  `strain_trend`, `long_term_trends`, `daily_frame`.
* STUBBED (need Hevy=Phase 2 / Samsung=Phase 3): `recovery_vs_load`,
  `sleep_vs_performance`, `hr_zones_per_workout`, `strength_progression`. They
  return [] today (frontend renders an empty state) and are filled in later phases
  WITHOUT signature changes.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _rows(conn: sqlite3.Connection, sql: str, params=()) -> List[Dict[str, Any]]:
    cur = conn.execute(sql, params)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _date_clause(start: Optional[str], end: Optional[str], col: str = "local_day"):
    clauses, params = [], []
    if start:
        clauses.append(f"{col} >= ?")
        params.append(start)
    if end:
        clauses.append(f"{col} <= ?")
        params.append(end)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def _rolling(records: List[Dict[str, Any]], field: str, window: int, out: str) -> None:
    """Attach a trailing simple moving average `out` for `field` over `window` days.

    Operates in place. Uses only non-null values within the window; if none are
    present the SMA is None. Records must be sorted ascending by day.
    """
    vals: List[Optional[float]] = [r.get(field) for r in records]
    for i, r in enumerate(records):
        lo = max(0, i - window + 1)
        chunk = [v for v in vals[lo : i + 1] if v is not None]
        r[out] = round(sum(chunk) / len(chunk), 2) if chunk else None


# --------------------------------------------------------------------------- #
# IMPLEMENTED NOW -- Whoop-only (Phase 1)
# --------------------------------------------------------------------------- #
def daily_frame(
    conn: sqlite3.Connection,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Full `day` rows in a date range, ascending by local_day.

    The base frame the dashboard filters on. Columns are exactly the `day` table
    (recovery/sleep/strain now; Hevy load columns present but NULL until Phase 2).

    Returns: list[dict] keyed by `local_day`.
    """
    where, params = _date_clause(start, end)
    return _rows(conn, f"SELECT * FROM day{where} ORDER BY local_day", params)


def recovery_trend(
    conn: sqlite3.Connection,
    start: Optional[str] = None,
    end: Optional[str] = None,
    windows=(7, 28),
) -> List[Dict[str, Any]]:
    """Recovery, resting HR, and HRV per day with rolling means (insight #4).

    Returns list[dict] keyed by `local_day`, each with: recovery_score, resting_hr,
    hrv_rmssd_ms, plus `<metric>_sma<window>` columns for each window in `windows`.
    """
    where, params = _date_clause(start, end)
    recs = _rows(
        conn,
        "SELECT local_day, recovery_score, resting_hr, hrv_rmssd_ms FROM day"
        f"{where} ORDER BY local_day",
        params,
    )
    for w in windows:
        _rolling(recs, "recovery_score", w, f"recovery_score_sma{w}")
        _rolling(recs, "resting_hr", w, f"resting_hr_sma{w}")
        _rolling(recs, "hrv_rmssd_ms", w, f"hrv_rmssd_ms_sma{w}")
    return recs


def sleep_trend(
    conn: sqlite3.Connection,
    start: Optional[str] = None,
    end: Optional[str] = None,
    windows=(7, 28),
) -> List[Dict[str, Any]]:
    """Sleep performance/duration/stages per day with rolling means (insight #4).

    Returns list[dict] keyed by `local_day` with sleep_perf_pct, total_sleep_min,
    sleep_eff_pct, rem_min, sws_min plus `<metric>_sma<window>` columns.
    """
    where, params = _date_clause(start, end)
    recs = _rows(
        conn,
        "SELECT local_day, sleep_perf_pct, total_sleep_min, sleep_eff_pct, rem_min, "
        f"sws_min FROM day{where} ORDER BY local_day",
        params,
    )
    for w in windows:
        _rolling(recs, "sleep_perf_pct", w, f"sleep_perf_pct_sma{w}")
        _rolling(recs, "total_sleep_min", w, f"total_sleep_min_sma{w}")
    return recs


def strain_trend(
    conn: sqlite3.Connection,
    start: Optional[str] = None,
    end: Optional[str] = None,
    windows=(7, 28),
) -> List[Dict[str, Any]]:
    """Daily Whoop strain with rolling means (insight #4).

    Returns list[dict] keyed by `local_day` with day_strain and its SMAs.
    """
    where, params = _date_clause(start, end)
    recs = _rows(
        conn,
        f"SELECT local_day, day_strain FROM day{where} ORDER BY local_day",
        params,
    )
    for w in windows:
        _rolling(recs, "day_strain", w, f"day_strain_sma{w}")
    return recs


def long_term_trends(
    conn: sqlite3.Connection,
    start: Optional[str] = None,
    end: Optional[str] = None,
    windows=(7, 28),
) -> Dict[str, List[Dict[str, Any]]]:
    """Insight #4 bundle: recovery, sleep, and strain trends together.

    Returns a dict with keys 'recovery', 'sleep', 'strain', each a list[dict] as
    produced by the respective *_trend function. Convenience for the trends tab.
    """
    return {
        "recovery": recovery_trend(conn, start, end, windows),
        "sleep": sleep_trend(conn, start, end, windows),
        "strain": strain_trend(conn, start, end, windows),
    }


# --------------------------------------------------------------------------- #
# STUBBED -- cross-source (filled in later phases; signatures are STABLE)
# --------------------------------------------------------------------------- #
def recovery_vs_load(
    conn: sqlite3.Connection,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Insight #1: recovery vs training load (NEEDS HEVY -- Phase 2).

    Planned return: list[dict] keyed by `local_day` with recovery_score, day_strain,
    hevy_volume_kg, hevy_set_count, acute_load_7d, chronic_load_28d, acwr, and
    next_day_recovery. Returns [] until Phase 2 fills the Hevy load columns in `day`.
    """
    return []


def sleep_vs_performance(
    conn: sqlite3.Connection,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Insight #2: sleep -> next-day performance (NEEDS HEVY -- Phase 2).

    Planned return: list[dict] keyed by `local_day` with sleep_perf_pct,
    total_sleep_min, rem_min (the night woken into that day, per the wake-date rule)
    and same-day hevy_volume_kg + per-key-lift top set. Returns [] until Phase 2.
    """
    return []


def hr_zones_per_workout(
    conn: sqlite3.Connection,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Insight #3: HR zones per workout (NEEDS SAMSUNG HR + align -- Phases 3-4).

    Planned return: list[dict] keyed by `session_id` with session_origin, title,
    local_day, kind, hr_mean/max/min, zone1..zone5 seconds and %, and flags
    ('estimated end' / 'possible clock offset'). Returns [] until Phases 3-4.
    """
    return []


def strength_progression(
    conn: sqlite3.Connection,
    lift: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Insight #4 (strength half): per-lift e1RM progression (NEEDS HEVY -- Phase 2).

    Planned return: list[dict] keyed by `local_day` with exercise_name, top_weight_kg,
    top_reps, and estimated_1rm = weight * (1 + reps/30). `lift` filters to one
    exercise. Returns [] until Phase 2 fills the hevy_* tables.
    """
    return []
