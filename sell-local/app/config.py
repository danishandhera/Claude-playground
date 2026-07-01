"""Application configuration, sourced from environment variables with safe defaults.

Keep all tunables here so nothing is hardcoded deeper in the app. No secrets
belong in the repo — read them from the environment.
"""
import os
from pathlib import Path

# Project root = the sell-local/ directory (one level above this file's package).
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Database ---------------------------------------------------------------
# Single SQLite file. Override with SELL_LOCAL_DB for tests / alt environments.
DB_PATH = os.environ.get("SELL_LOCAL_DB", str(BASE_DIR / "sell_local.db"))

# --- Contact rendering gate (Architecture §4) -------------------------------
# 'public'  -> render_contact() shows the raw number inline (Phase 1 default).
# 'gated'   -> render_contact() shows a "Reveal contact" htmx button instead.
# The raw contact is ALWAYS stored regardless of this flag.
CONTACT_MODE = os.environ.get("CONTACT_MODE", "public").strip().lower()

# --- Listings ---------------------------------------------------------------
DEFAULT_EXPIRY_DAYS = int(os.environ.get("DEFAULT_EXPIRY_DAYS", "30"))
PAGE_SIZE = int(os.environ.get("PAGE_SIZE", "24"))

# --- Display timezone (Architecture: store UTC, render Asia/Dubai) ----------
DISPLAY_TZ = os.environ.get("DISPLAY_TZ", "Asia/Dubai")
