"""Configuration loading: config.toml (non-secret) + .env (secrets).

ARCHITECTURE.md §2: tokens and home-tz live in config; secrets never committed.
Config decisions (home tz = Asia/Dubai, HR zones = Karvonen) come from
config.toml so nothing is hardcoded inline.

On Python 3.11+ this uses stdlib `tomllib`. On 3.9/3.10 it falls back to `tomli`
if installed, else a tiny built-in reader for the flat/[table] subset config.toml
uses -- so the tool stays runnable for offline testing without extra deps.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

# Project root = the directory containing this package's parent (repo root).
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent


# --------------------------------------------------------------------------- #
# TOML loading (with graceful fallback)
# --------------------------------------------------------------------------- #
def _load_toml(path: Path) -> Dict[str, Any]:
    try:
        import tomllib  # Python 3.11+

        with path.open("rb") as fh:
            return tomllib.load(fh)
    except ModuleNotFoundError:
        pass
    try:
        import tomli  # Python 3.9/3.10 backport

        with path.open("rb") as fh:
            return tomli.load(fh)
    except ModuleNotFoundError:
        return _mini_toml(path.read_text(encoding="utf-8"))


def _mini_toml(text: str) -> Dict[str, Any]:
    """Minimal TOML reader for the [table] + key = value subset config.toml uses.

    Supports nested tables via dotted headers ([a.b.c]), strings, ints, floats,
    bools, and single-line arrays of numbers/strings. Not a general TOML parser --
    only enough for our own config file when tomllib/tomli are unavailable.
    """
    root: Dict[str, Any] = {}
    cur = root
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            cur = root
            for part in line[1:-1].strip().split("."):
                cur = cur.setdefault(part.strip(), {})
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        cur[key.strip()] = _parse_value(val.strip())
    return root


def _parse_value(val: str) -> Any:
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [_parse_value(v.strip()) for v in inner.split(",") if v.strip()]
    if (val.startswith('"') and val.endswith('"')) or (
        val.startswith("'") and val.endswith("'")
    ):
        return val[1:-1]
    if val.lower() in ("true", "false"):
        return val.lower() == "true"
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        return val


# --------------------------------------------------------------------------- #
# .env loading (secrets)
# --------------------------------------------------------------------------- #
def _load_env(path: Path) -> None:
    """Load KEY=VALUE lines from a .env into os.environ (does not override existing).

    Uses python-dotenv if available; otherwise a minimal parser. Existing env
    vars win so CI/shell overrides are respected.
    """
    if not path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False)
        return
    except ModuleNotFoundError:
        pass
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


# --------------------------------------------------------------------------- #
# Public Config object
# --------------------------------------------------------------------------- #
class Config:
    """Loaded helthi configuration (non-secret settings + resolved secrets)."""

    def __init__(self, data: Dict[str, Any], project_root: Path):
        self._data = data
        self.project_root = project_root

    # -- convenience accessors -------------------------------------------- #
    @property
    def home_tz(self) -> str:
        return self._data.get("general", {}).get("home_tz", "Asia/Dubai")

    @property
    def db_path(self) -> Path:
        raw = self._data.get("general", {}).get("db_path", "helthi.db")
        p = Path(raw).expanduser()
        return p if p.is_absolute() else self.project_root / p

    @property
    def hr_zone_thresholds(self):
        return self._data.get("hr_zones", {}).get(
            "thresholds", [0.50, 0.60, 0.70, 0.80, 0.90]
        )

    @property
    def hr_zone_model(self) -> str:
        return self._data.get("hr_zones", {}).get("model", "karvonen")

    @property
    def age_years(self) -> int:
        return int(self._data.get("hr_zones", {}).get("age_years", 0) or 0)

    @property
    def max_hr_override(self) -> int:
        return int(self._data.get("hr_zones", {}).get("max_hr_override", 0) or 0)

    @property
    def whoop_backfill_start(self) -> str:
        return (
            self._data.get("sources", {})
            .get("whoop", {})
            .get("backfill_start", "")
        )

    def source_path(self, source: str, kind: str) -> Path:
        """Return an absolute path for a source inbox/archive folder."""
        raw = self._data.get("sources", {}).get(source, {}).get(kind, "")
        p = Path(raw).expanduser()
        return p if p.is_absolute() else self.project_root / p

    @property
    def hr_pad_seconds(self) -> int:
        return int(self._data.get("align", {}).get("hr_pad_seconds", 60))

    @property
    def assumed_session_minutes(self) -> int:
        return int(self._data.get("align", {}).get("assumed_session_minutes", 60))

    # -- secrets (from environment / .env) -------------------------------- #
    @property
    def whoop_client_id(self) -> str:
        return os.environ.get("WHOOP_CLIENT_ID", "")

    @property
    def whoop_client_secret(self) -> str:
        return os.environ.get("WHOOP_CLIENT_SECRET", "")

    @property
    def whoop_redirect_uri(self) -> str:
        return os.environ.get("WHOOP_REDIRECT_URI", "http://localhost:8080/callback")

    @property
    def whoop_token_path(self) -> Path:
        raw = os.environ.get("WHOOP_TOKEN_PATH", "")
        if raw:
            return Path(raw).expanduser()
        return Path.home() / ".config" / "helthi" / "whoop_token.json"

    def raw(self) -> Dict[str, Any]:
        return self._data


def load_config(
    config_path: Path = None, env_path: Path = None, project_root: Path = None
) -> Config:
    """Load config.toml + .env and return a Config.

    Paths default to the project root. Load order: .env first (so secrets are in
    the environment), then config.toml.
    """
    root = project_root or PROJECT_ROOT
    cfg_path = config_path or (root / "config.toml")
    dotenv_path = env_path or (root / ".env")

    _load_env(dotenv_path)
    data = _load_toml(cfg_path) if cfg_path.exists() else {}
    return Config(data, root)
