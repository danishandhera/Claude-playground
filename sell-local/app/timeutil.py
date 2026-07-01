"""UTC-in-DB -> Asia/Dubai-in-UI rendering helpers."""
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo  # py3.9+
except ImportError:  # pragma: no cover
    ZoneInfo = None

from .config import DISPLAY_TZ


def _parse(iso: str) -> datetime:
    """Parse a stored ISO-8601 string; assume UTC if it is naive."""
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def to_display(iso: str, fmt: str = "%d %b %Y, %H:%M") -> str:
    """Render a stored UTC timestamp in the configured display timezone."""
    if not iso:
        return ""
    dt = _parse(iso)
    if ZoneInfo is not None:
        try:
            dt = dt.astimezone(ZoneInfo(DISPLAY_TZ))
        except Exception:
            dt = dt.astimezone(timezone.utc)
    return dt.strftime(fmt)


def to_display_date(iso: str) -> str:
    return to_display(iso, "%d %b %Y")
