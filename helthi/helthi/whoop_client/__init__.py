"""Vendored WHOOP API v2 client (OAuth2 + read-only data endpoints).

Vendored from hedgertronic/whoop (MIT, Copyright (c) 2022 Josh Hejka) at
commit `main` (2026). See LICENSE in this directory. Minimal adaptation:
`datetime.UTC` (Python 3.11+) is imported with a 3.9/3.10 fallback so the
module stays importable for offline testing on older interpreters. The
production target is Python 3.12 per ARCHITECTURE.md.

This is helthi's Whoop OAuth + endpoint layer; we do not hand-roll OAuth.
The normalization/join layer around it is helthi's own code.
"""

from whoop_client.auth import (
    AUTHORIZE_URL,
    DEFAULT_SCOPES,
    REVOKE_URL,
    TOKEN_URL,
    WhoopAuth,
)
from whoop_client.client import REQUEST_URL, WhoopClient

__all__ = [
    "AUTHORIZE_URL",
    "DEFAULT_SCOPES",
    "REQUEST_URL",
    "REVOKE_URL",
    "TOKEN_URL",
    "WhoopAuth",
    "WhoopClient",
]
