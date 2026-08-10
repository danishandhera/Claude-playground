"""Whoop OAuth authorization-code flow + token persistence (ARCHITECTURE.md §4.1).

Runs the one-time authorization-code flow against a local callback server
(default http://localhost:8080/callback), stores the token set to disk, and
provides an authenticated WhoopClient whose `on_token_refresh` callback rewrites
the rotated token (access + refresh) back to that file -- so headless nightly
sync keeps working via the `offline` scope.

Token file: JSON, mode 0600, default ~/.config/helthi/whoop_token.json (override
with WHOOP_TOKEN_PATH). Never committed (see .gitignore).
"""

from __future__ import annotations

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


# --------------------------------------------------------------------------- #
# Token persistence
# --------------------------------------------------------------------------- #
def save_token(token: dict, path: Path) -> None:
    """Persist the OAuth token JSON with restrictive permissions (0600)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(token), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    os.chmod(path, 0o600)


def load_token(path: Path) -> Optional[dict]:
    """Load a saved token, or None if the file is absent/empty."""
    path = Path(path)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else None


def make_refresh_callback(path: Path):
    """Return an on_token_refresh callback that persists the rotated token."""

    def _cb(token: dict) -> None:
        save_token(token, path)

    return _cb


# --------------------------------------------------------------------------- #
# Authenticated client factory
# --------------------------------------------------------------------------- #
def build_client(cfg):
    """Build an authenticated WhoopClient from a saved token.

    Wires the on_token_refresh persistence callback. Raises if no token exists yet
    (run `helthi auth` first).
    """
    # Check for a saved token BEFORE importing the OAuth stack, so a missing
    # token gives a clean "run auth first" message even if authlib isn't present.
    token = load_token(cfg.whoop_token_path)
    if token is None:
        raise RuntimeError(
            "No Whoop token found. Run `helthi auth` first "
            f"(expected token at {cfg.whoop_token_path})."
        )
    from whoop_client import WhoopClient  # lazy: offline tests don't need authlib

    return WhoopClient(
        client_id=cfg.whoop_client_id,
        client_secret=cfg.whoop_client_secret,
        token=token,
        on_token_refresh=make_refresh_callback(cfg.whoop_token_path),
    )


# --------------------------------------------------------------------------- #
# Local callback server for the authorization-code flow
# --------------------------------------------------------------------------- #
class _CallbackHandler(BaseHTTPRequestHandler):
    captured_path: Optional[str] = None

    def do_GET(self):  # noqa: N802 (http.server API)
        _CallbackHandler.captured_path = self.path
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h2>helthi: Whoop authorization received.</h2>"
            b"<p>You can close this tab and return to the terminal.</p></body></html>"
        )

    def log_message(self, *_args):  # silence default logging
        return


def run_auth_flow(cfg, open_browser: bool = True, timeout: int = 300) -> dict:
    """Run the interactive authorization-code flow; returns the fetched token.

    Starts a local HTTP server on the redirect URI's host/port, opens the Whoop
    consent URL, waits for the redirect, exchanges the code, persists the token.
    """
    from whoop_client import WhoopClient

    client = WhoopClient(
        client_id=cfg.whoop_client_id,
        client_secret=cfg.whoop_client_secret,
        redirect_uri=cfg.whoop_redirect_uri,
        on_token_refresh=make_refresh_callback(cfg.whoop_token_path),
    )

    auth_url, _state = client.authorization_url()

    parsed = urlparse(cfg.whoop_redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8080

    _CallbackHandler.captured_path = None
    server = HTTPServer((host, port), _CallbackHandler)
    server.timeout = timeout

    print("Open this URL in your browser to authorize helthi with Whoop:\n")
    print("  " + auth_url + "\n")
    if open_browser:
        try:
            webbrowser.open(auth_url)
        except Exception:
            pass
    print(f"Waiting for the Whoop redirect on {host}:{port} ...")

    # Serve requests until we capture the callback (handles favicon etc.).
    def _serve():
        while _CallbackHandler.captured_path is None:
            server.handle_request()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    t.join(timeout)
    server.server_close()

    if _CallbackHandler.captured_path is None:
        raise TimeoutError("Timed out waiting for the Whoop OAuth redirect.")

    authorization_response = (
        f"{cfg.whoop_redirect_uri.split('?')[0]}{_CallbackHandler.captured_path}"
    )
    token = client.fetch_token(authorization_response=authorization_response)
    save_token(token, cfg.whoop_token_path)
    client.close()
    return token
