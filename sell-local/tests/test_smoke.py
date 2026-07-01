"""M0/M1 smoke tests: DB layer + all public routes against a seeded temp DB.

Run:  python -m pytest -q      (or)   python -m tests.test_smoke
"""
import os
import tempfile

# Point the app at a throwaway DB before importing app modules.
_TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP.close()
os.environ["SELL_LOCAL_DB"] = _TMP.name

from fastapi.testclient import TestClient  # noqa: E402

from app.db import connect, init_db  # noqa: E402
from app.main import app  # noqa: E402
from scripts.init_db import seed  # noqa: E402


def _setup():
    conn = connect()
    init_db(conn)
    seed(conn)
    conn.close()


def run():
    _setup()
    client = TestClient(app)
    checks = []

    def check(name, cond):
        checks.append((name, cond))
        print(("PASS" if cond else "FAIL"), name)

    # Landing lists communities.
    r = client.get("/")
    check("landing 200", r.status_code == 200)
    check("landing shows Dubai Marina", "Dubai Marina" in r.text)

    # Community browse shows approved listings.
    r = client.get("/c/dubai-marina")
    check("community 200", r.status_code == 200)
    check("community shows PS5 listing", "PS5" in r.text)

    # Unknown community -> 404.
    r = client.get("/c/nope")
    check("unknown community 404", r.status_code == 404)

    # FTS search (full page).
    r = client.get("/c/dubai-marina", params={"q": "bike"})
    check("search page 200", r.status_code == 200)
    check("search finds Trek bike", "Trek" in r.text)
    check("search excludes PS5", "PS5" not in r.text)

    # htmx search fragment endpoint.
    r = client.get("/c/jvc/search", params={"q": "stroller"})
    check("search fragment 200", r.status_code == 200)
    check("fragment finds stroller", "stroller" in r.text.lower())

    # Listing detail passes public predicate + shows contact (public mode).
    conn = connect()
    row = conn.execute(
        "SELECT id FROM listing WHERE title LIKE 'PS5%'"
    ).fetchone()
    conn.close()
    lid = row["id"]
    r = client.get(f"/listing/{lid}")
    check("listing detail 200", r.status_code == 200)
    check("detail shows contact number", "+971" in r.text)

    # Reveal-contact endpoint returns the number.
    r = client.get(f"/api/listings/{lid}/contact")
    check("reveal contact 200", r.status_code == 200)
    check("reveal shows number", "+971" in r.text)

    # Non-existent / non-public listing -> 404.
    r = client.get("/listing/999999")
    check("missing listing 404", r.status_code == 404)

    failed = [n for n, c in checks if not c]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} passed")
    if failed:
        raise SystemExit("FAILURES: " + ", ".join(failed))
    print("ALL SMOKE CHECKS PASSED")


# pytest entry point
def test_smoke():
    run()


if __name__ == "__main__":
    run()
