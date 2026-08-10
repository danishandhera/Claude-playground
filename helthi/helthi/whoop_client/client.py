"""WHOOP API v2 client and read-only data endpoints.

Vendored from hedgertronic/whoop (MIT). `WhoopClient` extends `WhoopAuth` with
the WHOOP data endpoints (profile, body measurement, cycles, recovery, sleep,
workouts). Collection endpoints page through `next_token` automatically.

Attributes:
    REQUEST_URL (str): Base URL for v2 data requests.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

try:  # Python 3.11+
    from datetime import UTC
except ImportError:  # Python 3.9/3.10 fallback for offline testing
    from datetime import timezone as _tz

    UTC = _tz.utc

from whoop_client.auth import WhoopAuth

REQUEST_URL = "https://api.prod.whoop.com/developer"


class WhoopClient(WhoopAuth):
    """Make read-only requests to the WHOOP v2 data API."""

    def __enter__(self):
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    ####################################################################################
    # API ENDPOINTS

    def get_profile(self) -> dict:
        """Get the user's basic profile."""
        return self._make_request(method="GET", url_slug="v2/user/profile/basic")

    def get_body_measurement(self) -> dict:
        """Get the user's body measurements (includes max_heart_rate)."""
        return self._make_request(method="GET", url_slug="v2/user/measurement/body")

    def get_cycle_collection(self, start_date=None, end_date=None) -> list:
        """Get all physiological cycles for a user (desc by start time)."""
        start, end = self._format_dates(start_date, end_date)
        return self._make_paginated_request(
            method="GET",
            url_slug="v2/cycle",
            params={"start": start, "end": end, "limit": 25},
        )

    def get_recovery_collection(self, start_date=None, end_date=None) -> list:
        """Get all recoveries for a user (desc by related sleep start time)."""
        start, end = self._format_dates(start_date, end_date)
        return self._make_paginated_request(
            method="GET",
            url_slug="v2/recovery",
            params={"start": start, "end": end, "limit": 25},
        )

    def get_sleep_collection(self, start_date=None, end_date=None) -> list:
        """Get all sleeps for a user (desc by start time)."""
        start, end = self._format_dates(start_date, end_date)
        return self._make_paginated_request(
            method="GET",
            url_slug="v2/activity/sleep",
            params={"start": start, "end": end, "limit": 25},
        )

    def get_workout_collection(self, start_date=None, end_date=None) -> list:
        """Get all workouts for a user (desc by start time)."""
        start, end = self._format_dates(start_date, end_date)
        return self._make_paginated_request(
            method="GET",
            url_slug="v2/activity/workout",
            params={"start": start, "end": end, "limit": 25},
        )

    ####################################################################################
    # API HELPER METHODS

    def _make_paginated_request(self, method: str, url_slug: str, **kwargs: Any) -> list:
        params = kwargs.pop("params", {})
        response_data: list = []

        while True:
            response = self._make_request(
                method=method,
                url_slug=url_slug,
                params=params,
                **kwargs,
            )

            response_data += response["records"]

            next_token = response.get("next_token")
            if next_token:
                params["nextToken"] = next_token
            else:
                break

        return response_data

    def _make_request(self, method: str, url_slug: str, **kwargs: Any) -> dict:
        response = self.session.request(
            method=method,
            url=f"{REQUEST_URL}/{url_slug}",
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    def _format_dates(self, start_date, end_date):
        today = datetime.now(UTC).date()
        start = self._format_collection_bound(
            start_date,
            default=datetime.combine(today - timedelta(days=6), time.min),
            end_bound=False,
        )
        end = self._format_collection_bound(
            end_date,
            default=datetime.combine(today + timedelta(days=1), time.min),
            end_bound=True,
        )

        if start >= end:
            raise ValueError(f"Start date greater than end date: {start} > {end}")

        return start.isoformat() + "Z", end.isoformat() + "Z"

    @staticmethod
    def _format_collection_bound(value, *, default: datetime, end_bound: bool):
        if value is None:
            return default

        raw_value = f"{value[:-1]}+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(raw_value)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(UTC).replace(tzinfo=None)

        is_datetime = "T" in value or " " in value
        if is_datetime:
            return parsed

        if end_bound:
            return datetime.combine(parsed.date() + timedelta(days=1), time.min)
        return datetime.combine(parsed.date(), time.min)
