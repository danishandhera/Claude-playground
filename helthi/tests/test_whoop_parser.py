"""Tests for the Whoop parser mapping + idempotent upsert."""

from parsers import whoop as wp


def test_map_cycle(whoop_sample, home_tz):
    row = wp.map_cycle(whoop_sample["cycles"][0], home_tz, "2026-07-31T00:00:00Z")
    assert row["source_id"] == "93801"
    assert row["start_utc"] == "2026-07-27T20:00:00Z"
    assert row["local_day"] == "2026-07-28"  # 20:00Z 07-27 = 00:00 07-28 Dubai
    assert row["strain"] == 12.5
    assert row["avg_hr"] == 70


def test_map_recovery_uses_cycle_day(whoop_sample):
    cycle_day = {"93801": "2026-07-28"}
    row = wp.map_recovery(whoop_sample["recoveries"][0], cycle_day, "2026-07-31T00:00:00Z")
    assert row["source_id"] == "93801"          # no own id -> cycle_id
    assert row["cycle_id"] == "93801"
    assert row["local_day"] == "2026-07-28"
    assert row["recovery_score"] == 66
    assert row["resting_hr"] == 52
    assert row["hrv_rmssd_ms"] == 45.2


def test_map_sleep_wake_date_and_minutes(whoop_sample, home_tz):
    row = wp.map_sleep(whoop_sample["sleeps"][0], home_tz, "2026-07-31T00:00:00Z")
    assert row["local_day"] == "2026-07-28"     # wake date
    assert row["is_nap"] == 0
    # light 12.6M + sws 7.2M + rem 5.4M ms -> 25.2M ms = 420 min asleep
    assert row["total_sleep_min"] == 420
    assert row["rem_min"] == 90
    assert row["sws_min"] == 120
    assert row["sleep_perf_pct"] == 90
    assert row["disturbances"] == 3


def test_map_workout(whoop_sample, home_tz):
    row = wp.map_workout(whoop_sample["workouts"][0], home_tz, "2026-07-31T00:00:00Z")
    assert row["sport_name"] == "running"
    assert row["max_hr"] == 155
    assert row["local_day"] == "2026-07-28"


def test_load_payloads_idempotent(db, whoop_sample, home_tz):
    s = whoop_sample
    n1 = wp.load_payloads(db, home_tz, s["cycles"], s["recoveries"], s["sleeps"], s["workouts"])
    # 2 cycles + 2 recoveries + 3 sleeps + 1 workout = 8
    assert n1 == 8
    # Re-run: same row counts, no duplicates (upsert on source_id).
    wp.load_payloads(db, home_tz, s["cycles"], s["recoveries"], s["sleeps"], s["workouts"])
    assert db.execute("SELECT COUNT(*) c FROM whoop_cycle").fetchone()["c"] == 2
    assert db.execute("SELECT COUNT(*) c FROM whoop_recovery").fetchone()["c"] == 2
    assert db.execute("SELECT COUNT(*) c FROM whoop_sleep").fetchone()["c"] == 3
    assert db.execute("SELECT COUNT(*) c FROM whoop_workout").fetchone()["c"] == 1


def test_recovery_backfills_cycle_day_from_db(db, whoop_sample, home_tz):
    s = whoop_sample
    # Load cycles first (separate run), then recoveries alone -> local_day resolved from db.
    wp.load_payloads(db, home_tz, s["cycles"], [], [], [])
    wp.load_payloads(db, home_tz, [], s["recoveries"], [], [])
    row = db.execute(
        "SELECT local_day FROM whoop_recovery WHERE source_id='93801'"
    ).fetchone()
    assert row["local_day"] == "2026-07-28"
