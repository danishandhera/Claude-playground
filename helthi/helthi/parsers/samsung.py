"""Samsung Health parser -- SCAFFOLD ONLY (implemented in Phase 3, gated on a real sample).

The riskiest source (ARCHITECTURE.md §4.3, Risk #1). Format quirks to bake in
when implemented: first line is a `com.samsung.shealth.*` metadata banner
(skiprows=1); strip the column prefix; timestamps are epoch MILLISECONDS plus a
separate `time_offset` (ms) -> normalize via time_align.epoch_ms_to_utc_iso
keeping raw epoch-ms + offset; HR lives in per-record nested JSON files referenced
from the exercise CSV -> follow refs into samsung_hr; integer activity codes map
to labels via a lookup. Idempotency by sha256 per file (processed_file), archive
hash-renamed. Cross-check current export shape against davidmosiah/samsung-health-mcp.

BLOCKED ON USER: provide one real Samsung Health export to finalize the parser.
"""

from __future__ import annotations

NotImplementedMessage = (
    "Samsung ingest is scaffolded for Phase 3 and blocked on a real export sample."
)

# Samsung integer activity-code -> label. Seeded; extended against a real sample.
ACTIVITY_CODES = {
    1001: "walking",
    1002: "running",
    11007: "cycling",
    13001: "hiking",
    14001: "strength_training",
}


def ingest_export(conn, cfg, path):
    """Ingest a Samsung export (folder of CSVs / single CSV / zip). Deferred."""
    raise NotImplementedError(NotImplementedMessage)


def scan_inbox(conn, cfg):
    """Scan the Samsung inbox folder and ingest new exports. Deferred."""
    raise NotImplementedError(NotImplementedMessage)
