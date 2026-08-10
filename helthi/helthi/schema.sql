-- helthi schema -- source of truth for the data model (ARCHITECTURE.md §3).
-- Three layers: raw per-source landing -> unified core -> derived (views).
-- All timestamps are ISO-8601 UTC text. Upserts key on (source, source_id).
-- Idempotent: safe to apply repeatedly (all CREATE ... IF NOT EXISTS).

PRAGMA foreign_keys = ON;

-- ============================================================================
-- 3.1 RAW LAYER (landing zone, faithful to source)
-- ============================================================================

-- ---- WHOOP ----
-- Whoop's fundamental unit is the "physiological cycle" (roughly a day,
-- anchored to the user's last sleep). Recovery and strain attach to a cycle;
-- sleeps are separate objects.

CREATE TABLE IF NOT EXISTS whoop_cycle (
  source_id      TEXT PRIMARY KEY,      -- Whoop cycle id
  start_utc      TEXT NOT NULL,
  end_utc        TEXT,                  -- null while cycle is in progress
  local_day      DATE NOT NULL,         -- derived (home tz) -- the "day" this cycle represents
  strain         REAL,                  -- day strain (0-21 scale)
  avg_hr         INTEGER,
  kilojoule      REAL,
  raw_json       TEXT,                  -- full payload, for re-derivation
  ingested_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS whoop_recovery (
  source_id      TEXT PRIMARY KEY,      -- recovery id (1:1 with a cycle)
  cycle_id       TEXT REFERENCES whoop_cycle(source_id),
  local_day      DATE NOT NULL,
  recovery_score INTEGER,               -- 0-100
  resting_hr     INTEGER,
  hrv_rmssd_ms   REAL,
  spo2_pct       REAL,
  skin_temp_c    REAL,
  raw_json       TEXT,
  ingested_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS whoop_sleep (
  source_id        TEXT PRIMARY KEY,    -- Whoop sleep id
  start_utc        TEXT NOT NULL,
  end_utc          TEXT NOT NULL,
  local_day        DATE NOT NULL,       -- day this sleep "belongs to" (wake date, home tz)
  is_nap           INTEGER DEFAULT 0,
  total_in_bed_min INTEGER,
  total_sleep_min  INTEGER,
  sleep_perf_pct   INTEGER,             -- Whoop sleep performance %
  sleep_eff_pct    REAL,
  rem_min          INTEGER,
  sws_min          INTEGER,             -- slow-wave (deep)
  light_min        INTEGER,
  awake_min        INTEGER,
  disturbances     INTEGER,
  raw_json         TEXT,
  ingested_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS whoop_workout (
  source_id      TEXT PRIMARY KEY,      -- Whoop workout id (cardio/activity, NOT strength sets)
  start_utc      TEXT NOT NULL,
  end_utc        TEXT NOT NULL,
  local_day      DATE NOT NULL,
  sport_name     TEXT,
  strain         REAL,
  avg_hr         INTEGER,
  max_hr         INTEGER,
  kilojoule      REAL,
  raw_json       TEXT,
  ingested_at    TEXT NOT NULL
);

-- ---- HEVY (strength: workout -> exercises -> sets; CSV export only, no API) ----
-- Scaffolded per design; parser implemented in a LATER phase.
CREATE TABLE IF NOT EXISTS hevy_workout (
  source_id      TEXT PRIMARY KEY,      -- synthesized hash (no server id available in CSV)
  start_utc      TEXT NOT NULL,         -- home-tz wall-clock localized -> UTC (CSV has no offset)
  end_utc        TEXT,
  local_day      DATE NOT NULL,
  title          TEXT,
  description    TEXT,
  source_file    TEXT,                  -- provenance = archived CSV hash
  ingested_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hevy_exercise (
  id             INTEGER PRIMARY KEY,   -- local surrogate
  workout_id     TEXT NOT NULL REFERENCES hevy_workout(source_id),
  order_idx      INTEGER,
  exercise_name  TEXT NOT NULL,         -- e.g. 'Barbell Squat'
  exercise_key   TEXT,                  -- Hevy template id if present, else slug(name)
  notes          TEXT,
  UNIQUE(workout_id, order_idx)
);

CREATE TABLE IF NOT EXISTS hevy_set (
  id             INTEGER PRIMARY KEY,   -- local surrogate
  exercise_id    INTEGER NOT NULL REFERENCES hevy_exercise(id),
  set_idx        INTEGER,
  set_type       TEXT,                  -- normal | warmup | failure | dropset
  weight_kg      REAL,
  reps           INTEGER,
  rpe            REAL,
  distance_m     REAL,                  -- for cardio-typed Hevy sets
  duration_sec   INTEGER,
  UNIQUE(exercise_id, set_idx)
);

-- ---- SAMSUNG (HR time series + exercise sessions) ----
-- Scaffolded per design; parser implemented in a LATER phase.
CREATE TABLE IF NOT EXISTS samsung_hr (
  id             INTEGER PRIMARY KEY,
  ts_utc         TEXT NOT NULL,         -- derived: epoch_ms - time_offset -> UTC, ISO-8601
  ts_epoch_ms    INTEGER NOT NULL,      -- raw local epoch-ms as exported (audit)
  tz_offset_ms   INTEGER,               -- time_offset applied (may be null in old exports)
  bpm            INTEGER NOT NULL,
  session_ref    TEXT,                  -- Samsung exercise source_id this HR record belongs to
  source_file    TEXT NOT NULL,         -- provenance = archived filename/JSON hash
  UNIQUE(ts_epoch_ms, bpm, source_file) -- dedup guard for overlapping exports
);
CREATE INDEX IF NOT EXISTS idx_samsung_hr_ts ON samsung_hr(ts_utc);

CREATE TABLE IF NOT EXISTS samsung_exercise (
  source_id      TEXT PRIMARY KEY,      -- Samsung session UUID (or hash if absent)
  start_utc      TEXT NOT NULL,         -- derived from epoch_ms + time_offset
  end_utc        TEXT NOT NULL,
  start_epoch_ms INTEGER NOT NULL,      -- raw (audit)
  tz_offset_ms   INTEGER,
  local_day      DATE NOT NULL,
  exercise_type  TEXT,                  -- Samsung integer activity code -> label (lookup map)
  mean_hr        INTEGER,
  max_hr         INTEGER,
  calories       REAL,
  hr_json_ref    TEXT,                  -- path/id of the nested JSON HR file for this session
  source_file    TEXT,
  ingested_at    TEXT NOT NULL
);

-- ---- INGEST BOOKKEEPING ----
CREATE TABLE IF NOT EXISTS ingest_run (
  id            INTEGER PRIMARY KEY,
  source        TEXT NOT NULL,          -- whoop | hevy | samsung
  started_at    TEXT NOT NULL,
  finished_at   TEXT,
  status        TEXT,                   -- ok | partial | error
  rows_upserted INTEGER,
  cursor        TEXT,                   -- e.g. Whoop 'updated since' watermark
  note          TEXT
);

CREATE TABLE IF NOT EXISTS processed_file (  -- Hevy/Samsung CSV idempotency
  file_hash    TEXT PRIMARY KEY,        -- sha256 of file contents
  filename     TEXT,
  processed_at TEXT NOT NULL,
  rows         INTEGER
);

-- ============================================================================
-- 3.2 UNIFIED CORE (source-agnostic entities; populated by unify.py)
-- ============================================================================

-- One row per calendar day (home tz). The spine everything joins to.
CREATE TABLE IF NOT EXISTS day (
  local_day        DATE PRIMARY KEY,
  -- recovery (Whoop)
  recovery_score   INTEGER,
  resting_hr       INTEGER,
  hrv_rmssd_ms     REAL,
  -- sleep (Whoop, the sleep whose wake-date = this day)
  sleep_perf_pct   INTEGER,
  total_sleep_min  INTEGER,
  sleep_eff_pct    REAL,
  rem_min          INTEGER,
  sws_min          INTEGER,
  -- strain (Whoop cycle)
  day_strain       REAL,
  -- training load (derived from Hevy for this day; filled in a LATER phase)
  hevy_volume_kg     REAL,             -- sum(weight_kg * reps) over working sets
  hevy_set_count     INTEGER,
  hevy_workout_count INTEGER,
  built_at         TEXT
);

-- One row per training session, source-agnostic. Currently Hevy-sourced;
-- Whoop/Samsung cardio sessions can also land here later.
CREATE TABLE IF NOT EXISTS session (
  id               INTEGER PRIMARY KEY,
  session_origin   TEXT NOT NULL,       -- 'hevy' | 'whoop' | 'samsung'
  origin_id        TEXT NOT NULL,       -- source_id in the origin raw table
  start_utc        TEXT NOT NULL,
  end_utc          TEXT,
  local_day        DATE NOT NULL REFERENCES day(local_day),
  kind             TEXT,                -- 'strength' | 'cardio'
  title            TEXT,
  volume_kg        REAL,                -- if strength
  -- HR summary, filled by the align step from samsung_hr (LATER phase):
  hr_samples       INTEGER,
  hr_mean          INTEGER,
  hr_max           INTEGER,
  hr_min           INTEGER,
  note             TEXT,                -- e.g. 'estimated end', 'possible clock offset'
  UNIQUE(session_origin, origin_id)
);

-- Per-session time in each HR zone (seconds). Produced by the align step (LATER phase).
CREATE TABLE IF NOT EXISTS session_hr_zone (
  session_id       INTEGER NOT NULL REFERENCES session(id),
  zone             INTEGER NOT NULL,    -- 1..5
  seconds          INTEGER NOT NULL,
  PRIMARY KEY (session_id, zone)
);

-- ============================================================================
-- 3.3(d) DERIVED VIEWS (overlap computed on read, not materialized)
-- ============================================================================

CREATE VIEW IF NOT EXISTS session_overlap AS
SELECT a.id AS session_id, b.id AS overlaps_id, b.session_origin AS overlaps_origin
FROM session a JOIN session b
  ON a.id <> b.id
 AND a.local_day = b.local_day
 AND a.start_utc < COALESCE(b.end_utc, b.start_utc)
 AND COALESCE(a.end_utc, a.start_utc) > b.start_utc;

-- ============================================================================
-- SUPPORTING INDICES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_whoop_cycle_day    ON whoop_cycle(local_day);
CREATE INDEX IF NOT EXISTS idx_whoop_recovery_day ON whoop_recovery(local_day);
CREATE INDEX IF NOT EXISTS idx_whoop_recovery_cyc ON whoop_recovery(cycle_id);
CREATE INDEX IF NOT EXISTS idx_whoop_sleep_day    ON whoop_sleep(local_day);
CREATE INDEX IF NOT EXISTS idx_whoop_workout_day  ON whoop_workout(local_day);
CREATE INDEX IF NOT EXISTS idx_hevy_workout_day   ON hevy_workout(local_day);
CREATE INDEX IF NOT EXISTS idx_session_day        ON session(local_day);
CREATE INDEX IF NOT EXISTS idx_samsung_ex_day     ON samsung_exercise(local_day);
