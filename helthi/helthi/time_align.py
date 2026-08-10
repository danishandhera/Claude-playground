"""Time-alignment layer -- the heart of the product (ARCHITECTURE.md §3.3).

Reconciles three time languages into canonical ISO-8601 UTC, derives the home-tz
"day" concept (including the sleep wake-date rule), and provides Karvonen HR-zone
bucketing. Whoop-specific parsing is implemented now; Samsung epoch-ms/offset and
Hevy naive-localize helpers are provided for later phases.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover -- Python <3.9
    ZoneInfo = None  # type: ignore


# --------------------------------------------------------------------------- #
# Timezone resolution (tolerant of missing system tzdata)
# --------------------------------------------------------------------------- #
def get_tz(tz_name: str):
    """Return a tzinfo for `tz_name`.

    Prefers stdlib zoneinfo. If the system/tzdata lookup fails (some minimal
    macOS/Python installs lack the Olson DB and the `tzdata` package isn't
    installed), fall back to a fixed UTC+4 offset for Asia/Dubai (our locked home
    tz, which has no DST) so offline testing still works. Other zones raise.
    """
    if ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    if tz_name in ("Asia/Dubai", "Etc/GMT-4"):
        return timezone(timedelta(hours=4), name="Asia/Dubai")
    if tz_name in ("UTC", "Etc/UTC"):
        return timezone.utc
    raise RuntimeError(
        f"Could not load timezone {tz_name!r}. Install the `tzdata` package "
        f"(pip install tzdata) or use a zone helthi can resolve offline."
    )


# --------------------------------------------------------------------------- #
# (a) Everything -> canonical UTC
# --------------------------------------------------------------------------- #
def parse_iso_to_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp (Whoop-style, with offset or 'Z') to aware UTC.

    Whoop timestamps are trustworthy ISO-8601 with an explicit offset -- no
    guessing. Returns a timezone-aware datetime in UTC.
    """
    if value is None:
        raise ValueError("Cannot parse None as a timestamp")
    v = value.strip()
    # Python's fromisoformat accepts 'Z' only on 3.11+; normalize for older too.
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        # Whoop always carries an offset; a naive value here is a data error.
        raise ValueError(f"Whoop timestamp lacked an offset: {value!r}")
    return dt.astimezone(timezone.utc)


def to_utc_iso(dt: datetime) -> str:
    """Render an aware datetime as canonical ISO-8601 UTC text ('...Z')."""
    return (
        dt.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def normalize_whoop_ts(value: str) -> str:
    """Whoop ISO-8601 -> canonical UTC ISO text. Convenience wrapper."""
    return to_utc_iso(parse_iso_to_utc(value))


def epoch_ms_to_utc_iso(epoch_ms: int, time_offset_ms: Optional[int]) -> str:
    """Samsung epoch-ms(+offset) -> UTC ISO (LATER phase helper).

    Samsung exports local epoch-ms plus a separate `time_offset` (ms). UTC =
    epoch_ms - time_offset. If the offset is missing (legacy export) we treat the
    epoch as already-UTC and the caller should flag it.
    """
    offset = time_offset_ms or 0
    dt = datetime.fromtimestamp((epoch_ms - offset) / 1000.0, tz=timezone.utc)
    return to_utc_iso(dt)


def naive_localize_to_utc_iso(naive_wallclock: str, home_tz: str) -> str:
    """Hevy CSV wall-clock (no offset) -> UTC ISO via home tz (LATER phase helper).

    Hevy CSV has no offset at all; interpret the wall-clock in the configured home
    tz then convert to UTC. This is the only source needing the home-tz assumption.
    """
    tz = get_tz(home_tz)
    v = naive_wallclock.strip().replace(" ", "T")
    naive = datetime.fromisoformat(v)
    if naive.tzinfo is not None:
        naive = naive.replace(tzinfo=None)
    localized = naive.replace(tzinfo=tz)
    return to_utc_iso(localized)


# --------------------------------------------------------------------------- #
# (b) The "day" concept
# --------------------------------------------------------------------------- #
def local_day(utc_iso: str, home_tz: str) -> str:
    """Home-tz calendar date (YYYY-MM-DD) of a UTC ISO instant.

    local_day = (start_utc converted to home_tz).date(). Used for cycles,
    recovery, workouts, Hevy, Samsung (when-it-happened rule).
    """
    tz = get_tz(home_tz)
    dt = parse_iso_to_utc(utc_iso).astimezone(tz)
    return dt.date().isoformat()


def sleep_wake_day(end_utc_iso: str, home_tz: str) -> str:
    """Wake-date rule (ARCHITECTURE.md §3.3b) for a sleep.

    A sleep belongs to the day you WOKE UP into: local_day = end_utc's date in
    home tz. This makes today's `day.sleep_*` the night you woke into today, which
    is what makes "sleep -> next-day performance" clean.
    """
    return local_day(end_utc_iso, home_tz)


# --------------------------------------------------------------------------- #
# HR zones -- Karvonen / heart-rate reserve (config-driven)
# --------------------------------------------------------------------------- #
def resolve_max_hr(
    whoop_max_hr: Optional[int],
    age_years: int,
    max_hr_override: int,
) -> Optional[int]:
    """Resolve the max HR to use for Karvonen zones.

    Priority: explicit override > Whoop body-measurement max_hr > (220 - age).
    Returns None if none are available.
    """
    if max_hr_override and max_hr_override > 0:
        return int(max_hr_override)
    if whoop_max_hr and whoop_max_hr > 0:
        return int(whoop_max_hr)
    if age_years and age_years > 0:
        return 220 - int(age_years)
    return None


def karvonen_zone_bounds(
    resting_hr: int, max_hr: int, thresholds: List[float]
) -> List[float]:
    """Absolute BPM lower-bounds for each HR zone using Karvonen (HRR) method.

    target_bpm = resting_hr + frac * (max_hr - resting_hr), where frac is a % of
    Heart Rate Reserve. Returns the lower BPM bound of each zone (len == thresholds).
    Zone i (1-based) covers [bounds[i-1], bounds[i]); the top zone is open-ended.
    """
    hrr = max_hr - resting_hr
    return [resting_hr + frac * hrr for frac in thresholds]


def zone_for_bpm(bpm: int, bounds: List[float]) -> int:
    """Which zone (1..len(bounds)) a heart-rate sample falls in.

    Below zone-1's lower bound is clamped to zone 1 (still "some effort" per the
    Karvonen model at rest). At/above the last bound is the top zone.
    """
    zone = 1
    for i, b in enumerate(bounds):
        if bpm >= b:
            zone = i + 1
    return zone
