-- Sell Local — SQLite schema (Architecture §3)
-- Timestamps are UTC ISO-8601 TEXT. Rendered in Asia/Dubai in the UI.
-- FTS5 + WAL required. Nothing is ever deleted for expiry — it's a query filter.

-- --- community --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS community (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    slug       TEXT    NOT NULL UNIQUE,
    is_active  INTEGER NOT NULL DEFAULT 1,      -- boolean; hide without deleting
    created_at TEXT    NOT NULL
);

-- --- listing ----------------------------------------------------------------
-- status: 'pending' | 'approved' | 'rejected' | 'postponed'
--   (laravel-moderation semantics; new rows land 'pending', invisible until approved)
-- source: 'web_form' | 'whatsapp'
CREATE TABLE IF NOT EXISTS listing (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    community_id     INTEGER NOT NULL REFERENCES community(id),
    title            TEXT,                       -- LLM-extracted
    description      TEXT,                       -- LLM-extracted
    price            INTEGER,                    -- whole AED; NULL = ask/free
    currency         TEXT    NOT NULL DEFAULT 'AED',
    contact          TEXT,                       -- raw phone/handle, always stored
    image_url        TEXT,                       -- NULL if none
    source           TEXT    NOT NULL,           -- 'web_form' | 'whatsapp'
    raw_text         TEXT    NOT NULL,           -- original message, for re-parse/audit
    status           TEXT    NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending','approved','rejected','postponed')),
    moderated_by     TEXT,                       -- admin id/name; NULL until acted on
    moderated_at     TEXT,                       -- decision timestamp
    reject_reason    TEXT,                       -- optional audit / sender feedback
    parse_confidence REAL,                       -- 0..1 from parse step
    created_at       TEXT    NOT NULL,           -- post date shown to users
    expires_at       TEXT    NOT NULL            -- default created_at + 30d
);

-- Indexes for the hot public read: filter by community + status + expiry, sort by recency.
CREATE INDEX IF NOT EXISTS idx_listing_public
    ON listing (community_id, status, expires_at, created_at);
CREATE INDEX IF NOT EXISTS idx_listing_status
    ON listing (status, created_at);          -- admin queue scans by status

-- --- listing_fts (FTS5 external-content over listing) -----------------------
CREATE VIRTUAL TABLE IF NOT EXISTS listing_fts
    USING fts5(title, description, content='listing', content_rowid='id');

-- Keep the FTS index in sync with the base table.
CREATE TRIGGER IF NOT EXISTS listing_ai AFTER INSERT ON listing BEGIN
    INSERT INTO listing_fts(rowid, title, description)
    VALUES (new.id, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS listing_ad AFTER DELETE ON listing BEGIN
    INSERT INTO listing_fts(listing_fts, rowid, title, description)
    VALUES ('delete', old.id, old.title, old.description);
END;

CREATE TRIGGER IF NOT EXISTS listing_au AFTER UPDATE ON listing BEGIN
    INSERT INTO listing_fts(listing_fts, rowid, title, description)
    VALUES ('delete', old.id, old.title, old.description);
    INSERT INTO listing_fts(rowid, title, description)
    VALUES (new.id, new.title, new.description);
END;
