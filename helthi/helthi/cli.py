"""helthi CLI (ARCHITECTURE.md §2).

Subcommands:
  init           create/upgrade the SQLite db from schema.sql
  auth           run the Whoop OAuth authorization-code flow, persist the token
  sync           pull Whoop -> raw tables (idempotent), then build-unified
  build-unified  rebuild the unified `day` layer from raw (re-runnable)
  status         show db + ingest health
  ingest         file-drop sources (hevy|samsung) -- scaffolded, later phases
  watch          folder watcher for file-drop sources -- scaffolded, later phases
  dash           launch the Streamlit dashboard (FRONTEND owns app.py)

Run: `python -m helthi.cli <subcommand>` or, if installed, `helthi <subcommand>`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow both `python -m helthi.cli` and `python -m cli` (with the inner package
# dir on PYTHONPATH). Ensure the inner package dir is importable as a source root
# so the flat intra-package imports (config, db, parsers, whoop_client) resolve.
_PKG_DIR = str(Path(__file__).resolve().parent)
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

from config import load_config
from db import apply_schema, connect, init_db, last_cursor


def _open(cfg):
    return init_db(cfg.db_path)


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_init(cfg, args) -> int:
    conn = connect(cfg.db_path)
    apply_schema(conn)
    print(f"Initialized db at {cfg.db_path}")
    conn.close()
    return 0


def cmd_auth(cfg, args) -> int:
    from auth_flow import run_auth_flow

    if not cfg.whoop_client_id or not cfg.whoop_client_secret:
        print(
            "WHOOP_CLIENT_ID / WHOOP_CLIENT_SECRET not set. Copy .env.example to "
            ".env and fill them in.",
            file=sys.stderr,
        )
        return 2
    try:
        run_auth_flow(cfg, open_browser=not args.no_browser)
    except ModuleNotFoundError as exc:
        print(
            f"Missing dependency for Whoop auth ({exc.name}). Install runtime deps: "
            "pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 2
    print(f"Token saved to {cfg.whoop_token_path}")
    return 0


def cmd_sync(cfg, args) -> int:
    from auth_flow import build_client
    from parsers import whoop as whoop_parser
    from unify import build_unified

    conn = _open(cfg)

    start = args.start
    if start is None and not args.full:
        # Steady-state: resume from the watermark if we have one.
        wm = last_cursor(conn, "whoop")
        start = wm[:10] if wm else cfg.whoop_backfill_start or None
    elif args.full:
        start = cfg.whoop_backfill_start or None

    try:
        client = build_client(cfg)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ModuleNotFoundError as exc:
        print(
            f"Missing dependency for Whoop sync ({exc.name}). Install runtime deps: "
            "pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 2

    try:
        summary = whoop_parser.sync(conn, cfg, client, start_date=start,
                                    end_date=args.end)
    finally:
        client.close()

    print(
        "Whoop sync {status}: {rows_upserted} rows "
        "(cycles={cycles} recovery={recoveries} sleep={sleeps} "
        "workouts={workouts})".format(**summary)
    )
    n = build_unified(conn)
    print(f"Built unified `day` table: {n} days")
    conn.close()
    return 0


def cmd_build_unified(cfg, args) -> int:
    from unify import build_unified

    conn = _open(cfg)
    n = build_unified(conn)
    print(f"Built unified `day` table from raw: {n} days")
    conn.close()
    return 0


def cmd_status(cfg, args) -> int:
    conn = _open(cfg)
    print(f"db: {cfg.db_path}")
    print(f"home_tz: {cfg.home_tz}   hr_zone_model: {cfg.hr_zone_model}")

    counts = {
        "whoop_cycle": None,
        "whoop_recovery": None,
        "whoop_sleep": None,
        "whoop_workout": None,
        "day": None,
        "session": None,
    }
    for t in counts:
        counts[t] = conn.execute(f"SELECT COUNT(*) AS c FROM {t}").fetchone()["c"]
    print("\nrow counts:")
    for t, c in counts.items():
        print(f"  {t:16} {c}")

    day_range = conn.execute(
        "SELECT MIN(local_day) AS lo, MAX(local_day) AS hi FROM day"
    ).fetchone()
    if day_range["lo"]:
        print(f"\nday range: {day_range['lo']} .. {day_range['hi']}")

    print("\nrecent ingest runs:")
    runs = conn.execute(
        "SELECT source, started_at, status, rows_upserted, note FROM ingest_run "
        "ORDER BY id DESC LIMIT 5"
    ).fetchall()
    if not runs:
        print("  (none yet)")
    for r in runs:
        note = f"  note={r['note']}" if r["note"] else ""
        print(
            f"  {r['source']:8} {r['started_at']} {r['status']:8} "
            f"rows={r['rows_upserted']}{note}"
        )
    conn.close()
    return 0


def cmd_ingest(cfg, args) -> int:
    print(
        f"`ingest {args.source}` is scaffolded for a later phase "
        f"(Hevy=Phase 2, Samsung=Phase 3) and not implemented yet.",
        file=sys.stderr,
    )
    return 3


def cmd_watch(cfg, args) -> int:
    print(
        "`watch` (folder watcher for Hevy/Samsung drops) is scaffolded for a "
        "later phase and not implemented yet.",
        file=sys.stderr,
    )
    return 3


def cmd_dash(cfg, args) -> int:
    app = Path(__file__).resolve().parent / "dashboard" / "app.py"
    print(f"Launch the dashboard (FRONTEND owns it) with:\n  streamlit run {app}")
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="helthi", description="Local fitness-data consolidator.")
    p.add_argument("--config", type=Path, default=None, help="path to config.toml")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create/upgrade the SQLite db from schema.sql")

    a = sub.add_parser("auth", help="run Whoop OAuth flow and persist the token")
    a.add_argument("--no-browser", action="store_true", help="print URL, don't auto-open")

    s = sub.add_parser("sync", help="pull Whoop into raw tables, then build-unified")
    s.add_argument("--start", default=None, help="ISO start date (default: watermark)")
    s.add_argument("--end", default=None, help="ISO end date (default: now)")
    s.add_argument("--full", action="store_true", help="ignore watermark; full backfill")

    sub.add_parser("build-unified", help="rebuild unified `day` from raw (re-runnable)")
    sub.add_parser("status", help="show db + ingest health")

    ing = sub.add_parser("ingest", help="file-drop sources (scaffolded)")
    ing.add_argument("source", choices=["hevy", "samsung"])
    ing.add_argument("--file", default=None)

    sub.add_parser("watch", help="folder watcher (scaffolded)")
    sub.add_parser("dash", help="how to launch the Streamlit dashboard")
    return p


_DISPATCH = {
    "init": cmd_init,
    "auth": cmd_auth,
    "sync": cmd_sync,
    "build-unified": cmd_build_unified,
    "status": cmd_status,
    "ingest": cmd_ingest,
    "watch": cmd_watch,
    "dash": cmd_dash,
}


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = load_config(config_path=args.config)
    return _DISPATCH[args.command](cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
