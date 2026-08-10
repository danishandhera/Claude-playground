"""Hevy CSV parser -- SCAFFOLD ONLY (implemented in Phase 2).

Hevy is file-drop only (no Hevy Pro -> no API). The CSV is one row per set with
workout/exercise/set columns. Phase 2 will: group rows -> hevy_workout ->
hevy_exercise -> hevy_set (schema modeled on remuzel/hevy-api), synthesize a
stable source_id = hash(title + start_utc + ordered set fingerprint) for
idempotency, localize the offset-less wall-clock via time_align.naive_localize_to_utc_iso
with the home tz, and compute working-set volume in unify (not at ingest).

Reuses the shared file-drop machinery (scan/hash/archive) that Phase 2 builds and
Samsung (Phase 3) reuses.
"""

from __future__ import annotations

NotImplementedMessage = (
    "Hevy CSV ingest is scaffolded for Phase 2 and not implemented yet."
)


def ingest_file(conn, cfg, file_path):
    """Parse one Hevy CSV export into raw tables. Deferred to Phase 2."""
    raise NotImplementedError(NotImplementedMessage)


def scan_inbox(conn, cfg):
    """Scan the Hevy inbox folder and ingest new files. Deferred to Phase 2."""
    raise NotImplementedError(NotImplementedMessage)
