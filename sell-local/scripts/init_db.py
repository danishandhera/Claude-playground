"""Initialise the SQLite DB and seed browsable sample data.

Usage (from the sell-local/ dir, venv active):
    python -m scripts.init_db          # create schema + seed if empty
    python -m scripts.init_db --reset  # drop the DB file first, then seed

Idempotent without --reset: it will not double-seed if listings already exist.
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

# Allow running as a script from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import DB_PATH  # noqa: E402
from app.db import connect, init_db  # noqa: E402


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


COMMUNITIES = [
    ("Arabian Ranches", "arabian-ranches"),
    ("Jumeirah Village Circle", "jvc"),
    ("Dubai Marina", "dubai-marina"),
    ("Mirdif", "mirdif"),
]

# (community_slug, title, description, price|None, contact, days_ago_posted, days_to_expiry)
LISTINGS = [
    ("arabian-ranches", "IKEA 3-seater sofa, grey",
     "Barely used grey fabric sofa from IKEA. No stains, pet-free home. Collection only from Al Reem.",
     650, "+971 50 123 4567", 1, 30),
    ("arabian-ranches", "Kids bicycle 16 inch",
     "Boys bike, suits ages 4-6. Training wheels included. Small scratches, works perfectly.",
     150, "+971 55 987 6543", 3, 27),
    ("arabian-ranches", "Moving out - free garden plants",
     "Leaving the country, giving away potted plants and two ceramic pots. First come first served.",
     None, "+971 52 111 2233", 0, 30),
    ("jvc", "Samsung 55\" 4K TV",
     "3 years old, excellent condition with remote and wall mount. Reason for sale: upgrading.",
     900, "+971 56 444 5566", 2, 28),
    ("jvc", "Dining table + 4 chairs",
     "Solid wood dining set, seats 4. Minor wear on one chair leg. Pickup from JVC district 12.",
     400, "+971 50 222 3344", 5, 25),
    ("jvc", "Baby stroller Chicco",
     "Chicco Bravo travel system, includes car seat adapter. Clean and folds easily.",
     300, "0509998877", 1, 29),
    ("dubai-marina", "PS5 with 2 controllers",
     "PlayStation 5 disc edition, two DualSense controllers and 3 games. Boxed.",
     1500, "+971 58 777 8899", 0, 30),
    ("dubai-marina", "Road bike Trek, size M",
     "Trek road bike, aluminium frame, recently serviced. Great for Marina/JBR rides.",
     1200, "trek.seller@example.com", 4, 26),
    ("dubai-marina", "Office chair Herman Miller Aeron",
     "Genuine Aeron size B, fully adjustable. Some desk wear but mechanism perfect.",
     1800, "+971 54 333 2211", 6, 24),
    ("mirdif", "Washing machine Bosch 8kg",
     "Bosch front-load 8kg, works great, selling because we're relocating. Can help load into car.",
     700, "+971 50 555 6677", 2, 28),
    ("mirdif", "Study desk + bookshelf",
     "White study desk with attached shelf, ideal for kids room or home office. Assembled.",
     250, "+971 55 121 3141", 7, 23),
]


def seed(conn) -> None:
    now = datetime.now(timezone.utc)

    # Communities (idempotent on slug).
    slug_to_id = {}
    for name, slug in COMMUNITIES:
        conn.execute(
            "INSERT OR IGNORE INTO community (name, slug, is_active, created_at) "
            "VALUES (?, ?, 1, ?)",
            (name, slug, _iso(now)),
        )
    conn.commit()
    for row in conn.execute("SELECT id, slug FROM community").fetchall():
        slug_to_id[row["slug"]] = row["id"]

    # Only seed listings if none exist, to stay idempotent.
    existing = conn.execute("SELECT COUNT(*) AS n FROM listing").fetchone()["n"]
    if existing:
        print(f"Listings already present ({existing}); skipping listing seed.")
        return

    for slug, title, desc, price, contact, days_ago, ttl in LISTINGS:
        created = now - timedelta(days=days_ago)
        expires = created + timedelta(days=ttl)
        conn.execute(
            "INSERT INTO listing "
            "(community_id, title, description, price, currency, contact, image_url, "
            " source, raw_text, status, moderated_by, moderated_at, parse_confidence, "
            " created_at, expires_at) "
            "VALUES (?, ?, ?, ?, 'AED', ?, NULL, 'web_form', ?, 'approved', 'seed', ?, 0.95, ?, ?)",
            (
                slug_to_id[slug], title, desc, price, contact,
                f"{title}\n{desc}\nContact: {contact}",  # synthetic raw_text
                _iso(created), _iso(created), _iso(expires),
            ),
        )
    conn.commit()
    print(f"Seeded {len(COMMUNITIES)} communities and {len(LISTINGS)} approved listings.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Init + seed the Sell Local DB.")
    ap.add_argument("--reset", action="store_true", help="Delete the DB file first.")
    args = ap.parse_args()

    if args.reset and os.path.exists(DB_PATH):
        for suffix in ("", "-wal", "-shm"):
            p = DB_PATH + suffix
            if os.path.exists(p):
                os.remove(p)
        print(f"Removed existing DB at {DB_PATH}")

    conn = connect()
    try:
        init_db(conn)
        print(f"Schema ready at {DB_PATH}")
        seed(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
