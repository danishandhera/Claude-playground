"""Whoop ingest: OAuth pull -> raw whoop_* tables (ARCHITECTURE.md §4.1).

Split into pure mapping functions (Whoop v2 JSON -> raw-table row dicts, unit-
testable offline against fixtures) and an orchestration function that pulls via
the vendored whoop_client, upserts idempotently, and logs to ingest_run.

Idempotency: every upsert keys on the Whoop object id (source_id); re-fetched
rows overwrite in place (Whoop recomputes scores days later -- take the newest).
Rate limits (100/min, 10k/day): a 429 handler with exponential backoff wraps the
collection pulls; collections page through next_token inside the client.
"""

from __future__ import annotations

import json
import time as _time
from typing import Any, Callable, Dict, List, Optional

from db import finish_ingest_run, now_utc_iso, start_ingest_run, upsert
from time_align import local_day, normalize_whoop_ts, sleep_wake_day


# --------------------------------------------------------------------------- #
# Pure mapping functions (Whoop v2 JSON -> raw row dicts)
# --------------------------------------------------------------------------- #
def _ms_to_min(v: Optional[float]) -> Optional[int]:
    return round(v / 60000.0) if v is not None else None


def _score(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Return obj['score'] if the record is SCORED, else an empty dict.

    Whoop records can be PENDING_SCORE / UNSCORABLE, in which case `score` is
    absent. We still land the row (start/end/ids) so the timeline is complete.
    """
    return obj.get("score") or {}


def map_cycle(obj: Dict[str, Any], home_tz: str, ingested_at: str) -> Dict[str, Any]:
    start_utc = normalize_whoop_ts(obj["start"])
    end_raw = obj.get("end")
    end_utc = normalize_whoop_ts(end_raw) if end_raw else None
    sc = _score(obj)
    return {
        "source_id": str(obj["id"]),
        "start_utc": start_utc,
        "end_utc": end_utc,
        "local_day": local_day(start_utc, home_tz),
        "strain": sc.get("strain"),
        "avg_hr": sc.get("average_heart_rate"),
        "kilojoule": sc.get("kilojoule"),
        "raw_json": json.dumps(obj, separators=(",", ":")),
        "ingested_at": ingested_at,
    }


def map_recovery(
    obj: Dict[str, Any], cycle_day_by_id: Dict[str, str], ingested_at: str
) -> Dict[str, Any]:
    """Map a recovery. Recovery has no own id -> source_id = its cycle_id (1:1).

    local_day is the cycle's day (looked up), so recovery joins 1:1 to the
    wake-date sleep for that cycle.
    """
    cycle_id = str(obj["cycle_id"])
    sc = _score(obj)
    return {
        "source_id": cycle_id,
        "cycle_id": cycle_id,
        "local_day": cycle_day_by_id.get(cycle_id, ""),
        "recovery_score": sc.get("recovery_score"),
        "resting_hr": sc.get("resting_heart_rate"),
        "hrv_rmssd_ms": sc.get("hrv_rmssd_milli"),
        "spo2_pct": sc.get("spo2_percentage"),
        "skin_temp_c": sc.get("skin_temp_celsius"),
        "raw_json": json.dumps(obj, separators=(",", ":")),
        "ingested_at": ingested_at,
    }


def map_sleep(obj: Dict[str, Any], home_tz: str, ingested_at: str) -> Dict[str, Any]:
    start_utc = normalize_whoop_ts(obj["start"])
    end_utc = normalize_whoop_ts(obj["end"])
    sc = _score(obj)
    stages = sc.get("stage_summary") or {}
    return {
        "source_id": str(obj["id"]),
        "start_utc": start_utc,
        "end_utc": end_utc,
        # Wake-date rule: a sleep belongs to the day you woke up into.
        "local_day": sleep_wake_day(end_utc, home_tz),
        "is_nap": 1 if obj.get("nap") else 0,
        "total_in_bed_min": _ms_to_min(stages.get("total_in_bed_time_milli")),
        "total_sleep_min": _sleep_total_min(stages),
        "sleep_perf_pct": sc.get("sleep_performance_percentage"),
        "sleep_eff_pct": sc.get("sleep_efficiency_percentage"),
        "rem_min": _ms_to_min(stages.get("total_rem_sleep_time_milli")),
        "sws_min": _ms_to_min(stages.get("total_slow_wave_sleep_time_milli")),
        "light_min": _ms_to_min(stages.get("total_light_sleep_time_milli")),
        "awake_min": _ms_to_min(stages.get("total_awake_time_milli")),
        "disturbances": stages.get("disturbance_count"),
        "raw_json": json.dumps(obj, separators=(",", ":")),
        "ingested_at": ingested_at,
    }


def _sleep_total_min(stages: Dict[str, Any]) -> Optional[int]:
    """Total asleep minutes = light + sws + rem (in-bed minus awake/no-data)."""
    parts = [
        stages.get("total_light_sleep_time_milli"),
        stages.get("total_slow_wave_sleep_time_milli"),
        stages.get("total_rem_sleep_time_milli"),
    ]
    if all(p is None for p in parts):
        return None
    return _ms_to_min(sum(p or 0 for p in parts))


def map_workout(obj: Dict[str, Any], home_tz: str, ingested_at: str) -> Dict[str, Any]:
    start_utc = normalize_whoop_ts(obj["start"])
    end_utc = normalize_whoop_ts(obj["end"])
    sc = _score(obj)
    return {
        "source_id": str(obj["id"]),
        "start_utc": start_utc,
        "end_utc": end_utc,
        "local_day": local_day(start_utc, home_tz),
        "sport_name": obj.get("sport_name") or _sport_label(obj.get("sport_id")),
        "strain": sc.get("strain"),
        "avg_hr": sc.get("average_heart_rate"),
        "max_hr": sc.get("max_heart_rate"),
        "kilojoule": sc.get("kilojoule"),
        "raw_json": json.dumps(obj, separators=(",", ":")),
        "ingested_at": ingested_at,
    }


def _sport_label(sport_id: Optional[int]) -> Optional[str]:
    """Best-effort label for a Whoop sport_id when sport_name is absent."""
    if sport_id is None:
        return None
    return f"sport_{sport_id}"


# --------------------------------------------------------------------------- #
# Rate-limit-aware retry wrapper
# --------------------------------------------------------------------------- #
def with_backoff(fn: Callable, *, max_retries: int = 5, base_delay: float = 1.0):
    """Call `fn()`, retrying on HTTP 429 with exponential backoff.

    Whoop caps at 100 req/min, 10k req/day. Personal nightly sync is far under,
    but backfill can brush the per-minute cap; back off and honor Retry-After.
    """
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 -- inspect for 429 then re-raise
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status != 429 or attempt >= max_retries:
                raise
            retry_after = _retry_after_seconds(exc)
            delay = retry_after if retry_after is not None else base_delay * (2 ** attempt)
            _time.sleep(delay)
            attempt += 1


def _retry_after_seconds(exc: Exception) -> Optional[float]:
    resp = getattr(exc, "response", None)
    if resp is None:
        return None
    val = resp.headers.get("Retry-After") if hasattr(resp, "headers") else None
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Upsert-from-payloads (pure DB, no network -- used by tests and by ingest)
# --------------------------------------------------------------------------- #
def load_payloads(
    conn,
    home_tz: str,
    cycles: List[dict],
    recoveries: List[dict],
    sleeps: List[dict],
    workouts: List[dict],
) -> int:
    """Upsert already-fetched Whoop collections into the raw tables. Idempotent.

    Returns the total number of rows upserted. This is the seam tests exercise
    with fixture JSON -- no network required.
    """
    ingested_at = now_utc_iso()
    n = 0

    cycle_day_by_id: Dict[str, str] = {}
    for c in cycles:
        row = map_cycle(c, home_tz, ingested_at)
        cycle_day_by_id[row["source_id"]] = row["local_day"]
        upsert(conn, "whoop_cycle", row, ["source_id"])
        n += 1

    # Recovery local_day needs its cycle's day; backfill from DB for cycles that
    # arrived in an earlier run and aren't in this batch.
    for r in recoveries:
        cid = str(r["cycle_id"])
        if cid not in cycle_day_by_id:
            got = conn.execute(
                "SELECT local_day FROM whoop_cycle WHERE source_id=?", (cid,)
            ).fetchone()
            if got:
                cycle_day_by_id[cid] = got["local_day"]
        upsert(conn, "whoop_recovery", map_recovery(r, cycle_day_by_id, ingested_at),
               ["source_id"])
        n += 1

    for s in sleeps:
        upsert(conn, "whoop_sleep", map_sleep(s, home_tz, ingested_at), ["source_id"])
        n += 1

    for w in workouts:
        upsert(conn, "whoop_workout", map_workout(w, home_tz, ingested_at),
               ["source_id"])
        n += 1

    conn.commit()
    return n


# --------------------------------------------------------------------------- #
# Orchestration: pull via whoop_client + persist (Phase 1 network path)
# --------------------------------------------------------------------------- #
def sync(conn, cfg, client, start_date: Optional[str] = None,
         end_date: Optional[str] = None) -> Dict[str, Any]:
    """Pull Whoop collections and upsert into raw tables. Logs to ingest_run.

    `client` is an authenticated whoop_client.WhoopClient. `start_date`/`end_date`
    are ISO strings; if start_date is None the caller/CLI supplies the backfill
    start or watermark. Returns a summary dict.
    """
    run_id = start_ingest_run(conn, "whoop")
    try:
        cycles = with_backoff(
            lambda: client.get_cycle_collection(start_date, end_date)
        )
        recoveries = with_backoff(
            lambda: client.get_recovery_collection(start_date, end_date)
        )
        sleeps = with_backoff(
            lambda: client.get_sleep_collection(start_date, end_date)
        )
        workouts = with_backoff(
            lambda: client.get_workout_collection(start_date, end_date)
        )

        n = load_payloads(conn, cfg.home_tz, cycles, recoveries, sleeps, workouts)

        # Watermark = newest updated_at seen this run (steady-state pulls stay tiny).
        watermark = _max_updated_at(cycles + recoveries + sleeps + workouts)
        finish_ingest_run(conn, run_id, "ok", rows_upserted=n, cursor=watermark)
        return {
            "status": "ok",
            "rows_upserted": n,
            "cycles": len(cycles),
            "recoveries": len(recoveries),
            "sleeps": len(sleeps),
            "workouts": len(workouts),
            "cursor": watermark,
        }
    except Exception as exc:  # noqa: BLE001
        finish_ingest_run(conn, run_id, "error", note=str(exc)[:500])
        raise


def _max_updated_at(objs: List[dict]) -> Optional[str]:
    stamps = [o.get("updated_at") for o in objs if o.get("updated_at")]
    return max(stamps) if stamps else None
