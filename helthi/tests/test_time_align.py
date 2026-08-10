"""Tests for the time-alignment layer -- tz handling, day rule, HR zones."""

import time_align as ta


def test_parse_iso_z_and_offset_to_utc():
    assert ta.normalize_whoop_ts("2026-07-28T03:10:00.000Z") == "2026-07-28T03:10:00Z"
    # +04:00 offset -> subtract 4h to get UTC
    assert ta.normalize_whoop_ts("2026-07-28T07:10:00+04:00") == "2026-07-28T03:10:00Z"


def test_naive_offsetless_timestamp_rejected():
    import pytest

    with pytest.raises(ValueError):
        ta.parse_iso_to_utc("2026-07-28T03:10:00")


def test_local_day_dubai_offset():
    # 20:00 UTC on 07-27 is 00:00 (midnight) on 07-28 in Dubai (UTC+4).
    assert ta.local_day("2026-07-27T20:00:00Z", "Asia/Dubai") == "2026-07-28"
    # 19:59 UTC on 07-27 is 23:59 on 07-27 in Dubai.
    assert ta.local_day("2026-07-27T19:59:00Z", "Asia/Dubai") == "2026-07-27"


def test_sleep_wake_date_rule():
    # Sleep ending 03:10 UTC = 07:10 Dubai -> belongs to the wake day 07-28.
    assert ta.sleep_wake_day("2026-07-28T03:10:00Z", "Asia/Dubai") == "2026-07-28"
    # A sleep that ends just after midnight UTC still resolves by Dubai wake time.
    assert ta.sleep_wake_day("2026-07-29T03:45:00Z", "Asia/Dubai") == "2026-07-29"


def test_epoch_ms_to_utc_with_offset():
    # local epoch-ms for 2026-07-28T12:00:00+04:00, offset +4h in ms.
    offset = 4 * 3600 * 1000
    # UTC instant we want back:
    from datetime import datetime, timezone

    utc = datetime(2026, 7, 28, 8, 0, 0, tzinfo=timezone.utc)
    local_epoch_ms = int(utc.timestamp() * 1000) + offset
    assert ta.epoch_ms_to_utc_iso(local_epoch_ms, offset) == "2026-07-28T08:00:00Z"


def test_naive_localize_hevy():
    # Hevy wall-clock 2026-07-28 20:00 in Dubai -> 16:00 UTC.
    assert (
        ta.naive_localize_to_utc_iso("2026-07-28 20:00:00", "Asia/Dubai")
        == "2026-07-28T16:00:00Z"
    )


def test_resolve_max_hr_priority():
    assert ta.resolve_max_hr(190, 30, 200) == 200  # override wins
    assert ta.resolve_max_hr(190, 30, 0) == 190     # whoop next
    assert ta.resolve_max_hr(None, 30, 0) == 190    # 220-age fallback
    assert ta.resolve_max_hr(None, 0, 0) is None


def test_karvonen_zone_bounds_and_bucketing():
    # resting 50, max 200 -> HRR 150. thresholds 50/60/70/80/90%.
    bounds = ta.karvonen_zone_bounds(50, 200, [0.5, 0.6, 0.7, 0.8, 0.9])
    # zone1 lower = 50 + 0.5*150 = 125; zone5 lower = 50 + 0.9*150 = 185
    assert bounds[0] == 125
    assert bounds[4] == 185
    assert ta.zone_for_bpm(100, bounds) == 1   # below z1 clamps to 1
    assert ta.zone_for_bpm(130, bounds) == 1
    assert ta.zone_for_bpm(140, bounds) == 2   # >= 50+0.6*150=140
    assert ta.zone_for_bpm(190, bounds) == 5
