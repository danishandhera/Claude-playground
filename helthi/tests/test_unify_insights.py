"""End-to-end on fixtures: load raw -> build_unified -> insights."""

from parsers import whoop as wp
from unify import build_unified
import insights


def _load(db, sample, tz):
    return wp.load_payloads(
        db, tz, sample["cycles"], sample["recoveries"], sample["sleeps"],
        sample["workouts"],
    )


def test_build_unified_populates_day(db, whoop_sample, home_tz):
    _load(db, whoop_sample, home_tz)
    n = build_unified(db)
    assert n == 2  # days 07-28 and 07-29

    d28 = db.execute("SELECT * FROM day WHERE local_day='2026-07-28'").fetchone()
    assert d28["recovery_score"] == 66
    assert d28["resting_hr"] == 52
    assert d28["day_strain"] == 12.5
    # The non-nap sleep (wake date 07-28) should win over the nap.
    assert d28["total_sleep_min"] == 420
    assert d28["sleep_perf_pct"] == 90

    d29 = db.execute("SELECT * FROM day WHERE local_day='2026-07-29'").fetchone()
    assert d29["recovery_score"] == 82
    assert d29["sleep_perf_pct"] == 95


def test_build_unified_is_rerunnable(db, whoop_sample, home_tz):
    _load(db, whoop_sample, home_tz)
    build_unified(db)
    build_unified(db)  # rebuild from raw -- reversibility
    assert db.execute("SELECT COUNT(*) c FROM day").fetchone()["c"] == 2


def test_nap_excluded_from_day_sleep(db, whoop_sample, home_tz):
    _load(db, whoop_sample, home_tz)
    build_unified(db)
    # nap on 07-28 had perf 20; day should show the real night's 90.
    d28 = db.execute("SELECT sleep_perf_pct FROM day WHERE local_day='2026-07-28'").fetchone()
    assert d28["sleep_perf_pct"] == 90


def test_insights_recovery_trend_and_rolling(db, whoop_sample, home_tz):
    _load(db, whoop_sample, home_tz)
    build_unified(db)
    recs = insights.recovery_trend(db, windows=(2,))
    assert [r["local_day"] for r in recs] == ["2026-07-28", "2026-07-29"]
    assert recs[0]["recovery_score"] == 66
    # 2-day SMA on day2 = mean(66, 82) = 74
    assert recs[1]["recovery_score_sma2"] == 74.0


def test_insights_long_term_bundle(db, whoop_sample, home_tz):
    _load(db, whoop_sample, home_tz)
    build_unified(db)
    bundle = insights.long_term_trends(db)
    assert set(bundle) == {"recovery", "sleep", "strain"}
    assert len(bundle["sleep"]) == 2


def test_stubs_return_empty(db, whoop_sample, home_tz):
    _load(db, whoop_sample, home_tz)
    build_unified(db)
    assert insights.recovery_vs_load(db) == []
    assert insights.sleep_vs_performance(db) == []
    assert insights.hr_zones_per_workout(db) == []
    assert insights.strength_progression(db) == []


def test_daily_frame_date_filter(db, whoop_sample, home_tz):
    _load(db, whoop_sample, home_tz)
    build_unified(db)
    only29 = insights.daily_frame(db, start="2026-07-29")
    assert [r["local_day"] for r in only29] == ["2026-07-29"]
