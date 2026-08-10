"""Build the unified layer from raw tables (ARCHITECTURE.md §3.2, §4.4).

`build_unified` rebuilds `day` (and, in later phases, `session`/`session_hr_zone`)
from raw. Idempotent full rebuild -- cheap at this data size and avoids
incremental-drift bugs. Re-runnable from raw at any time (reversibility): the raw
whoop_* tables are the source of truth, so changing a unify rule never needs a re-pull.

Phase 1 scope: `day` gets recovery + sleep + strain from Whoop. The Hevy training-
load columns (hevy_volume_kg/set_count/workout_count) and the `session` table are
populated in Phase 2; they stay NULL/empty here without breaking anything.
"""

from __future__ import annotations

import sqlite3
from typing import List

from db import now_utc_iso


def build_unified(conn: sqlite3.Connection) -> int:
    """Rebuild the unified `day` table from raw Whoop. Returns rows written.

    Full rebuild: clear `day`, then insert one row per home-tz calendar day that
    appears in any raw Whoop table, joining in recovery / sleep / cycle strain.
    """
    built_at = now_utc_iso()

    # Collect every local_day present across the raw Whoop tables. Sleep uses its
    # wake-date local_day (already stored per the wake-date rule in the parser),
    # so the join below lines the right night up with the right day.
    conn.execute("DELETE FROM day;")

    days = _all_whoop_days(conn)
    for d in days:
        recovery = conn.execute(
            "SELECT recovery_score, resting_hr, hrv_rmssd_ms FROM whoop_recovery "
            "WHERE local_day=? ORDER BY ingested_at DESC LIMIT 1",
            (d,),
        ).fetchone()

        # The main (non-nap) sleep whose wake-date is this day. Prefer the longest.
        sleep = conn.execute(
            "SELECT sleep_perf_pct, total_sleep_min, sleep_eff_pct, rem_min, sws_min "
            "FROM whoop_sleep WHERE local_day=? AND is_nap=0 "
            "ORDER BY total_sleep_min DESC, ingested_at DESC LIMIT 1",
            (d,),
        ).fetchone()

        # Day strain from the cycle representing this day (max if several).
        cycle = conn.execute(
            "SELECT strain FROM whoop_cycle WHERE local_day=? "
            "ORDER BY strain DESC LIMIT 1",
            (d,),
        ).fetchone()

        conn.execute(
            "INSERT INTO day ("
            "  local_day, recovery_score, resting_hr, hrv_rmssd_ms,"
            "  sleep_perf_pct, total_sleep_min, sleep_eff_pct, rem_min, sws_min,"
            "  day_strain, built_at"
            ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                d,
                recovery["recovery_score"] if recovery else None,
                recovery["resting_hr"] if recovery else None,
                recovery["hrv_rmssd_ms"] if recovery else None,
                sleep["sleep_perf_pct"] if sleep else None,
                sleep["total_sleep_min"] if sleep else None,
                sleep["sleep_eff_pct"] if sleep else None,
                sleep["rem_min"] if sleep else None,
                sleep["sws_min"] if sleep else None,
                cycle["strain"] if cycle else None,
                built_at,
            ),
        )

    conn.commit()
    return len(days)


def _all_whoop_days(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        "SELECT local_day FROM whoop_cycle "
        "UNION SELECT local_day FROM whoop_recovery "
        "UNION SELECT local_day FROM whoop_sleep "
        "UNION SELECT local_day FROM whoop_workout "
        "ORDER BY local_day"
    ).fetchall()
    return [r["local_day"] for r in rows if r["local_day"]]
