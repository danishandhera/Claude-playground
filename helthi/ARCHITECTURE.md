# helthi — Architecture Blueprint

Local fitness-data consolidator. Ingests Whoop, Hevy, and Samsung Health into one SQLite
database; serves a local web dashboard for cross-source insight. Single user, one machine
(M4 MacBook Air, 16GB).

Status: design locked, ready to build. This doc is the contract Frontend/Backend build from.

---

## 1. Goal & constraints (restated)

**Goal.** Break the three-app silo. Whoop knows recovery, Hevy knows the barbell, Samsung
knows heart rate — the value is in the *joins* none of them can do alone. Consolidate, then
compute four insights: (1) recovery vs training load, (2) sleep → next-day performance,
(3) HR zones per workout, (4) long-term trends.

**Constraints.**
- Single user, single machine, runs locally. No auth, no multi-tenant, no cloud deploy.
- Low-maintenance: this is a personal tool that runs for years with occasional attention.
- Consistent with household pattern (dubizzle-tool, food-compare): local Python + SQLite, a
  CLI/`--file` ingest workflow, a thin UI on top.
- **Build on prior art, don't reinvent** (see `PRIOR-ART.md`). Four vetted MIT pieces do the
  hard parts: `hedgertronic/whoop` (Whoop OAuth v2 + refresh), `sandseb123/Leo-Health-Core`
  (the overall architecture template — source-tagged SQLite + `parsers/` + folder watcher +
  local dashboard), `remuzel/hevy-api` (Hevy workout→exercise→set typed model as our schema
  reference), and `BlackFireAlex`/`davidmosiah/samsung-health-mcp` as Samsung format references.
  Our own code is the *normalization/join layer* that glues them.
- Data volume is tiny — a few years of daily records is <100k rows across all tables. SQLite
  is comfortable by three orders of magnitude. Nothing here needs to scale.

**Assumptions (stated, not blocking).**
- All timestamps are normalized to **UTC** on ingest; a single **home timezone** (default
  `Asia/Dubai`) is stored in config and used to derive the "day" concept and for display.
  Travel/timezone edge cases are handled but not optimized (see Risks).
- Whoop OAuth v2 app is registered by the user; we hold client id/secret + refresh token.
- **Whoop is the only API source.** Hevy and Samsung are both **file-drop (CSV export) only** —
  the user does not have Hevy Pro, so the Hevy API is out of scope entirely. This means exactly
  one OAuth/token path (Whoop) and two watched-folder parser paths (Hevy CSV, Samsung CSV).
- Samsung CSV schema is **not yet confirmed**. The parser is built against a documented-guess
  schema and finalized once we have a real export sample (flagged in Risks — this is the one
  genuine unknown).

**Non-goals.** Real-time streaming, mobile app, writing back to any source, sharing/export,
ML/predictions beyond simple rolling stats and correlations.

---

## 2. Stack

Lead recommendation, with one-line justification each:

| Layer | Choice | Why |
|---|---|---|
| Language | **Python 3.12** | Matches household pattern; best library coverage for HTTP, CSV, SQLite, dataframes. |
| Store | **SQLite** (locked) | Zero-ops, single file, perfect for single-user local scale. |
| DB access | **stdlib `sqlite3` + plain SQL** | No ORM. Schema is small and stable; SQL is clearer for the join layer than an ORM would be. Mirrors Leo-Health-Core's `db/ingest.py` pattern. |
| Whoop client | **`hedgertronic/whoop`** (MIT, vendored/pinned) | Authlib OAuth v2 + `offline` scope + `on_token_refresh` callback; don't write our own OAuth. |
| Ingestion | **Python scripts / CLI subcommands** (`helthi ingest whoop|hevy|samsung`) | Same `--file` + subcommand ergonomics as sibling tools. Runnable by hand or by cron/launchd. |
| HTTP | **`httpx`** | Whoop OAuth is the only HTTP source; sync is fine here, clean OAuth handling. |
| Folder watch | **`watchdog`** (optional) + idempotent rescan | Watches the drop folders for **both** Hevy and Samsung CSVs; ingest is also safe to re-run, so watching is a convenience not a dependency. |
| Dashboard | **Streamlit** | See decision below. |
| Charts | **Plotly** (via Streamlit) | Interactive zoom/hover for HR time series and trend lines; Streamlit-native. |
| Config/secrets | **`.env` (gitignored) + `config.toml`** | Tokens and home-tz live here; never committed. |

### Dashboard decision: Streamlit (recommended), Flask a close second

Now weighed against the prior-art template too — Leo-Health-Core (our architecture model) ships
a local **Flask** `dashboard.py`, which validates Flask + SQLite + folder-watcher as a proven
stack for exactly this shape of app.

- **Streamlit — chosen.** Pure Python, no separate frontend, no API/route layer, no templating.
  Four insight tabs, date-range filters, and Plotly charts come essentially free. One
  `streamlit run app.py`. For a single-user local dashboard whose value is *composed analytical
  views* (dual-axis overlays, scatters with r-values, per-lift small multiples), Streamlit gets
  there with the least code. Cost: re-runs top-to-bottom on interaction — irrelevant at our data
  size, cached with `@st.cache_data`.
- **Flask (Leo-Health-Core pattern) — strong runner-up, deliberately not chosen.** It's the
  validated template and worth mirroring *structurally* (source-tagged tables, `parsers/`,
  `db/ingest.py`, folder watcher — we adopt all of that). But its dashboard is hand-rolled
  routes + Jinja + a JS chart lib; for our four multi-panel analytical tabs that's materially
  more glue code than Streamlit for no benefit at single-user scale. We take Leo's *ingestion
  architecture* and swap its Flask view for Streamlit. If the dashboard ever needs custom
  layout/interactivity Streamlit can't express, Flask is the pre-vetted fallback.
- **Datasette — companion, not primary.** Superb for *exploring* `helthi.db` and debugging
  ingestion; point it at the same file for free. But table/SQL-oriented — fights the composed
  insight views. Keep on the side.
- **FastAPI + JS charts — rejected.** Splits into backend + frontend + build step; over-
  engineering for one local user.

**Net:** Leo-Health-Core's ingestion architecture + Streamlit dashboard + Datasette-on-the-side
for debugging. No FastAPI, no JS build, no ORM.

### Repo layout

```
helthi/
  README.md
  ARCHITECTURE.md
  pyproject.toml
  config.toml                # home_tz, hr zone thresholds, source paths
  .env                       # secrets (gitignored)
  helthi.db                  # SQLite (gitignored)
  data/
    inbox/hevy/              # watched drop folder for Hevy CSV exports
    inbox/samsung/           # watched drop folder for Samsung export (CSV + nested JSON)
    archive/hevy/            # processed files moved here, hash-named
    archive/samsung/         # processed files moved here, hash-named
  helthi/
    __init__.py
    cli.py                   # `helthi ingest ...`, `helthi build-unified`, `helthi watch`, `helthi dash`
    db.py                    # connection, migrations, upsert helpers (Leo `db/ingest.py` pattern)
    schema.sql               # DDL (source of truth for the model)
    config.py                # loads config.toml + .env
    time_align.py            # tz + epoch-ms/ISO normalization + day + session-overlap (the heart)
    whoop_client/            # vendored hedgertronic/whoop (MIT), pinned
    parsers/                 # per-source ingest (Leo-Health-Core convention)
      whoop.py               # OAuth pull via whoop_client + on_token_refresh persistence
      hevy.py                # CSV-only parser (no API — no Hevy Pro)
      samsung.py             # CSV banner-skip + epoch-ms + time_offset + nested-JSON HR reader
    unify.py                 # builds unified layer from raw tables
    insights.py              # the four computations (pure funcs over the DB)
    dashboard/app.py         # Streamlit entrypoint
  tests/
```

---

## 3. Data model

Three-layer design: **raw per-source** (faithful landing zone) → **unified core** (source-agnostic
entities) → **derived** (the day/session join + insight inputs). Raw tables let us re-derive
everything if unify logic changes, without re-pulling from APIs.

Conventions: all timestamps stored as **ISO-8601 UTC text** (`start_utc`, `end_utc`). Every raw
row carries `source`, a `source_id` (natural key from the provider), and `ingested_at`. Upserts
key on `(source, source_id)`. `local_day` is a `DATE` derived from `start_utc` in home tz.

### 3.1 Raw layer (landing zone, faithful to source)

```sql
-- ---- WHOOP ----
-- Whoop's fundamental unit is the "physiological cycle" (roughly a day, midnight-anchored to
-- the user's last sleep). Recovery and strain attach to a cycle; sleeps are separate objects.

CREATE TABLE whoop_cycle (
  source_id      TEXT PRIMARY KEY,      -- Whoop cycle id
  start_utc      TEXT NOT NULL,
  end_utc        TEXT,                  -- null while cycle is in progress
  local_day      DATE NOT NULL,         -- derived (home tz) — the "day" this cycle represents
  strain         REAL,                  -- day strain (0–21 scale)
  avg_hr         INTEGER,
  kilojoule      REAL,
  raw_json       TEXT,                  -- full payload, for re-derivation
  ingested_at    TEXT NOT NULL
);

CREATE TABLE whoop_recovery (
  source_id      TEXT PRIMARY KEY,      -- recovery id (1:1 with a cycle)
  cycle_id       TEXT REFERENCES whoop_cycle(source_id),
  local_day      DATE NOT NULL,
  recovery_score INTEGER,               -- 0–100
  resting_hr     INTEGER,
  hrv_rmssd_ms   REAL,
  spo2_pct       REAL,
  skin_temp_c    REAL,
  raw_json       TEXT,
  ingested_at    TEXT NOT NULL
);

CREATE TABLE whoop_sleep (
  source_id        TEXT PRIMARY KEY,    -- Whoop sleep id
  start_utc        TEXT NOT NULL,
  end_utc          TEXT NOT NULL,
  local_day        DATE NOT NULL,       -- the day this sleep "belongs to" (wake date, home tz)
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

CREATE TABLE whoop_workout (
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
CREATE TABLE hevy_workout (
  source_id      TEXT PRIMARY KEY,      -- synthesized hash (no server id available in CSV)
  start_utc      TEXT NOT NULL,         -- home-tz wall-clock localized -> UTC (CSV has no offset)
  end_utc        TEXT,
  local_day      DATE NOT NULL,
  title          TEXT,
  description    TEXT,
  source_file    TEXT,                  -- provenance = archived CSV hash
  ingested_at    TEXT NOT NULL
);

CREATE TABLE hevy_exercise (
  id             INTEGER PRIMARY KEY,   -- local surrogate
  workout_id     TEXT NOT NULL REFERENCES hevy_workout(source_id),
  order_idx      INTEGER,
  exercise_name  TEXT NOT NULL,         -- e.g. 'Barbell Squat'
  exercise_key   TEXT,                  -- Hevy template id if present, else slug(name)
  notes          TEXT,
  UNIQUE(workout_id, order_idx)
);

CREATE TABLE hevy_set (
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
-- Format reality (per PRIOR-ART.md, BlackFireAlex + davidmosiah/samsung-health-mcp):
--   * CSV first line is a metadata banner -> skiprows=1
--   * timestamps are epoch MILLISECONDS (not ISO); a separate `time_offset` (ms, e.g. +14400000
--     for UTC+4) gives local time. We store BOTH the derived UTC and the offset so the join
--     layer never has to guess a tz for Samsung rows (unlike Hevy CSV, which has none).
--   * column names are prefixed `com.samsung.shealth.*` -> strip on parse.
--   * HR is NOT inline in the CSV: the exercise CSV references per-record JSON files that hold
--     the actual HR series. The parser follows those references to populate samsung_hr.
CREATE TABLE samsung_hr (
  id             INTEGER PRIMARY KEY,
  ts_utc         TEXT NOT NULL,         -- derived: epoch_ms - time_offset -> UTC, ISO-8601
  ts_epoch_ms    INTEGER NOT NULL,      -- raw local epoch-ms as exported (audit)
  tz_offset_ms   INTEGER,               -- time_offset applied (may be null in old exports)
  bpm            INTEGER NOT NULL,
  session_ref    TEXT,                  -- Samsung exercise source_id this HR record belongs to
  source_file    TEXT NOT NULL,         -- provenance = archived filename/JSON hash
  UNIQUE(ts_epoch_ms, bpm, source_file) -- dedup guard for overlapping exports
);
CREATE INDEX idx_samsung_hr_ts ON samsung_hr(ts_utc);

CREATE TABLE samsung_exercise (
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
CREATE TABLE ingest_run (
  id           INTEGER PRIMARY KEY,
  source       TEXT NOT NULL,           -- whoop | hevy | samsung
  started_at   TEXT NOT NULL,
  finished_at  TEXT,
  status       TEXT,                    -- ok | partial | error
  rows_upserted INTEGER,
  cursor       TEXT,                    -- e.g. Whoop 'updated since' watermark
  note         TEXT
);

CREATE TABLE processed_file (          -- Samsung CSV idempotency
  file_hash    TEXT PRIMARY KEY,        -- sha256 of file contents
  filename     TEXT,
  processed_at TEXT NOT NULL,
  rows         INTEGER
);
```

### 3.2 Unified core (source-agnostic entities)

These are what insights read. Populated by `unify.py` from raw tables. Kept thin: they
normalize the *shape*, not invent data.

```sql
-- One row per calendar day (home tz). The spine everything joins to.
CREATE TABLE day (
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
  -- training load (derived from Hevy for this day)
  hevy_volume_kg   REAL,               -- sum(weight_kg * reps) over working sets
  hevy_set_count   INTEGER,
  hevy_workout_count INTEGER,
  built_at         TEXT
);

-- One row per training session, source-agnostic. Currently Hevy-sourced; Whoop/Samsung
-- cardio sessions can also land here later. This is the unit HR gets merged onto.
CREATE TABLE session (
  id               INTEGER PRIMARY KEY,
  session_origin   TEXT NOT NULL,       -- 'hevy' | 'whoop' | 'samsung'
  origin_id        TEXT NOT NULL,       -- source_id in the origin raw table
  start_utc        TEXT NOT NULL,
  end_utc          TEXT,
  local_day        DATE NOT NULL REFERENCES day(local_day),
  kind             TEXT,                -- 'strength' | 'cardio'
  title            TEXT,
  volume_kg        REAL,                -- if strength
  -- HR summary, filled by the align step from samsung_hr:
  hr_samples       INTEGER,
  hr_mean          INTEGER,
  hr_max           INTEGER,
  hr_min           INTEGER,
  UNIQUE(session_origin, origin_id)
);

-- Per-session time in each HR zone (seconds). Produced by the align step.
CREATE TABLE session_hr_zone (
  session_id       INTEGER NOT NULL REFERENCES session(id),
  zone             INTEGER NOT NULL,    -- 1..5
  seconds          INTEGER NOT NULL,
  PRIMARY KEY (session_id, zone)
);
```

### 3.3 The time-alignment layer (the heart of the product)

Three sources speak three different time languages. This layer reconciles them. It lives in
`time_align.py` and runs as part of `unify`/`build-unified`. Four distinct alignment problems:

**(a) Everything → canonical UTC on ingest — three different input formats.** This is the
concrete normalization the three sources force on us:

| Source | Raw time format | Normalization to UTC |
|---|---|---|
| **Whoop** | ISO-8601 with explicit offset | Parse ISO, convert to UTC. Trustworthy — no guessing. |
| **Samsung** | epoch **milliseconds** + separate `time_offset` (ms) | `utc = epoch_ms - time_offset`; store `ts_utc` (ISO) **and** keep `ts_epoch_ms` + `tz_offset_ms`. When `time_offset` is present the local tz is *known exactly* — no home-tz assumption needed. If a legacy export omits it, fall back to home tz and flag. |
| **Hevy CSV** | local wall-clock, **no offset at all** | Interpret in the **home tz** from config, then convert to UTC. This is the only source that genuinely requires the single-user home-tz assumption. |

So the normalization function is source-branched: ISO-parse (Whoop) vs epoch-ms-minus-offset
(Samsung) vs naive-localize-with-home-tz (Hevy). All three land as ISO-8601 UTC text in
`start_utc`/`ts_utc`, which is the *only* representation the day/session/HR-overlap logic below
ever sees. Keeping Samsung's raw epoch-ms + offset means we can re-derive if the offset handling
ever needs fixing without re-importing.

**(b) The "day" concept.** A day is a home-tz calendar date. `local_day = (start_utc converted
to home_tz).date()`. But sleep needs a rule: a sleep that starts 23:40 and ends 07:10 belongs
to the **wake day** (its `local_day` = end_utc's date), because Whoop recovery for a day is a
function of the sleep you woke up from. So:
- `whoop_sleep.local_day` = date of `end_utc` in home tz (wake date).
- `whoop_recovery.local_day` = its cycle's day; joins 1:1 to the wake-date sleep.
- Hevy/Samsung/workout `local_day` = date of `start_utc` in home tz (when it happened).
This asymmetry is deliberate and is *the* rule that makes "sleep → next-day performance" clean:
today's `day.sleep_*` is the night you woke into today; today's `day.hevy_volume_kg` is what
you lifted today. "Next-day performance" is then simply `day[d].sleep` vs `day[d].volume`.

**(c) HR series → session (the overlap join).** Merge Samsung HR onto each training session so
we get zones/effort per workout. Algorithm in `align_hr_to_sessions()`:
1. For each `session` (start_utc, end_utc), select `samsung_hr` rows where
   `ts_utc BETWEEN start-PAD AND end+PAD` (PAD ≈ 60s to catch watch/app clock skew).
2. If the session has no `end_utc` (Hevy CSV often omits it), estimate it: `end = start +
   median_session_duration` or `start + (set_count * assumed_set_seconds)`; flag as estimated.
3. Compute `hr_mean/max/min/samples` → write to `session`.
4. Bucket each HR sample into a zone (thresholds from config, see below) weighting by the gap
   to the next sample (so irregular sampling doesn't skew zone seconds) → write
   `session_hr_zone`.
5. Clock-skew guard: if a session finds *zero* HR samples but HR exists within ±10 min, record
   a `note` on the session ("possible clock offset") rather than silently showing empty zones.

**HR zones** are % of max HR (config: `hr_max` or age-derived `220-age`; default 5-zone Whoop-
style split at 50/60/70/80/90%). Stored as config so they're tunable without code change.

**(d) Session ↔ session dedup across sources.** A single gym session can appear as *both* a Hevy
strength workout and a Samsung exercise session (and maybe a Whoop workout). We don't merge them
into one row — each keeps its origin — but we tag overlaps so the dashboard can present them
together. An overlap = time ranges intersect on the same `local_day`. This is computed on read
(a view) rather than materialized, since it's cheap:

```sql
CREATE VIEW session_overlap AS
SELECT a.id AS session_id, b.id AS overlaps_id, b.session_origin AS overlaps_origin
FROM session a JOIN session b
  ON a.id <> b.id
 AND a.local_day = b.local_day
 AND a.start_utc < COALESCE(b.end_utc, b.start_utc)
 AND COALESCE(a.end_utc, a.start_utc) > b.start_utc;
```

**Why not one giant merged table?** Because merges are lossy and hard to unwind. Keeping raw
faithful + a thin unified layer + overlap-on-read means any join rule can be changed and
re-derived from raw with `helthi build-unified`, no re-pull. That reversibility is the design's
main insurance.

---

## 4. Ingestion design

General rule: **all ingest is idempotent.** Re-running any source is safe — upserts key on
`(source, source_id)`; Samsung dedups on file hash + row uniqueness. Every run logs to
`ingest_run`. Secrets live in `.env` (gitignored); nothing sensitive is committed.

### 4.1 Whoop (OAuth API v2, auto-pull — the ONLY API source)

Built on **`hedgertronic/whoop`** (MIT, vendored) — Authlib OAuth v2. Don't hand-roll OAuth.

- **Auth.** Authorization-code flow once with the `offline` scope (`authorize` at
  `api.prod.whoop.com/oauth/oauth2/auth`, `client_secret_post`). The client auto-refreshes the
  access token; we wire its **`on_token_refresh` callback** to persist the rotated token set
  (access + refresh) back to `.env`/a token file. `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, and
  the stored token JSON are the only secrets. Headless nightly sync works because `offline`
  keeps the refresh token alive; if refresh ever hard-fails, CLI prints a re-auth link.
- **Pull.** Cycles, recovery, sleep, workouts. Page through collections; use `updated_since`
  with the watermark in `ingest_run.cursor` (last successful `updated_at`). First run backfills
  full history; later runs pull only new/changed.
- **Upsert.** Keyed on Whoop object id (`source_id`). Re-fetched rows overwrite — Whoop can
  recompute scores days later, so always take the newest payload.
- **Rate limits.** 100 req/min, 10k req/day (per Whoop docs). Nightly personal sync is far under
  this; on 429, exponential backoff. Backfill paginates slowly. See Risks.

### 4.2 Hevy (CSV export only — no API, no Hevy Pro)

The Hevy API requires Hevy Pro, which the user does not have, so **Hevy is file-drop only** —
same watched-folder path as Samsung. No secrets, no HTTP.

- **Mechanism.** User exports from the Hevy app → drops the CSV into `data/inbox/hevy/` (or
  `helthi ingest hevy --file export.csv`). Same scan/watch/idempotency machinery as Samsung
  (§4.3): sha256 the file, skip if in `processed_file`, else parse → archive.
- **Parse.** Hevy CSV is one row per set with workout/exercise/set columns. Group rows →
  `hevy_workout` → `hevy_exercise` → `hevy_set`. Schema modeled on `remuzel/hevy-api`'s typed
  Workout→Exercise→Set (weight/reps/rpe) — see §3.1.
- **Stable id (no server id available).** Synthesize `source_id` = hash(title + start_utc +
  ordered exercise/set fingerprint) so re-importing the same or an extended export is
  idempotent. Re-imported workouts replace their children wholesale (delete + re-insert; a
  workout is small).
- **Volume.** `hevy_volume_kg` (working sets only, exclude warmup) computed in `unify`, not at
  ingest, so the rule is changeable.

### 4.3 Samsung Health (CSV + nested-JSON drop, folder watch)

The riskiest source. User exports from Samsung Health → drops the export (CSVs **plus** the
referenced JSON files, or a zip) into `data/inbox/samsung/`. Cross-check current export shape
against `davidmosiah/samsung-health-mcp` (2026); `BlackFireAlex` (2022) is an older reference.

- **Mechanism.** Same two triggers as Hevy: `helthi ingest samsung` scans the inbox, or
  `helthi watch` (`watchdog`) fires on new files. Scan is the source of truth; watch is a
  convenience. Handle folder-of-CSVs, single-CSV, and zipped variants (per samsung-health-mcp).
- **Parser — bake in the known format quirks:**
  - **Banner line:** first row is a `com.samsung.shealth.*` metadata banner → `skiprows=1`.
  - **Column prefixes:** strip the `com.samsung.shealth.<type>.` prefix from column names.
  - **Timestamps:** epoch **milliseconds** + a `time_offset` (ms) field → normalize to UTC per
    §3.3(a); keep raw epoch-ms and offset.
  - **Nested-JSON HR:** the exercise CSV does not hold HR inline — it references per-record JSON
    files (`hr_json_ref`). The parser follows those refs and expands them into `samsung_hr`.
  - **Activity codes:** `exercise_type` is an integer code → map to a label via a lookup table.
- **Idempotency.** sha256 each file (CSV *and* each JSON) → skip if in `processed_file`. Else
  parse, upsert, record hash, **move** file to `data/archive/samsung/` hash-renamed. Overlapping
  exports also caught by `samsung_hr`'s `UNIQUE(ts_epoch_ms, bpm, source_file)` + a dedup pass.
- **Finalize against a real sample.** Parser is written against the above documented guess and
  confirmed once the user provides one real export. Archived raw files mean a schema fix is a
  re-parse, never a re-export. **This gates Phase 3.**
- **No secrets** (file-based).

### 4.4 Unify / build

`helthi build-unified` (also auto-run at the end of each ingest): rebuilds `day`, `session`,
`session_hr_zone` from raw. Idempotent full rebuild is fine at this data size (cheap, and avoids
incremental-drift bugs). This is where 3.3's alignment logic executes.

---

## 5. The four insight computations

Each is a pure function in `insights.py` reading the unified layer, rendered as a Streamlit tab.

**1. Recovery vs training load.**
- Source: `day` (has `recovery_score`, `day_strain`, `hevy_volume_kg`, `hevy_set_count`).
- Compute: overlay recovery (0–100) against training load per day; rolling 7-day acute load and
  28-day chronic load → acute:chronic ratio (ACWR) as an overtraining flag. Correlate next-day
  recovery against today's volume/strain.
- Dashboard: dual-axis time series (recovery line vs volume bars); scatter (today volume →
  tomorrow recovery) with trend; a "load status" gauge (ACWR bands: under/optimal/overreaching).

**2. Sleep → next-day performance.**
- Source: `day` joined to itself / to `session`. Because of the wake-date rule (3.3b),
  `day[d].sleep_*` already *is* the night before today's training. Performance proxies:
  `day[d].hevy_volume_kg`, top-set weight per key lift (from `hevy_set`), session `hr_mean`.
- Compute: correlate sleep_perf_pct / total_sleep_min / rem_min against same-day volume and
  per-lift top set. Bucket nights into good/poor sleep, compare mean performance.
- Dashboard: scatter (sleep metric → performance) with r value; grouped bars (good vs poor
  sleep → avg volume, avg top-set); per-lift small multiples.

**3. Heart-rate zones per workout.**
- Source: `session`, `session_hr_zone` (from the HR-overlap join, 3.3c), joined to
  `hevy_workout`/`samsung_exercise` for type.
- Compute: per session, seconds/percent in zones 1–5; aggregate by workout type/title
  (e.g. "leg day" vs "push day" HR profile); effort = time in zone 4–5.
- Dashboard: per-session stacked HR-zone bar + the raw HR line (Plotly) with session window
  shaded; aggregate zone distribution by workout type; sessions flagged "estimated end" or
  "possible clock offset" clearly marked.

**4. Long-term trends.**
- Source: `day` (recovery, resting_hr, hrv, sleep) over time; `hevy_set` for strength
  progression (e3RM per key lift = weight×(1+reps/30)); session HR for aerobic drift.
- Compute: rolling means (7/28-day) for resting HR, HRV, recovery, sleep; estimated-1RM trend
  per lift; monthly summaries.
- Dashboard: multi-metric trend view with selectable range (30/90/365d/all); per-lift strength
  progression chart; resting-HR / HRV drift lines with rolling average.

Cross-cutting: a top-level date-range filter and a home-tz-aware calendar. `@st.cache_data` on
the query functions keyed by db mtime.

---

## 6. Phased build plan

Ordered so a useful, real dashboard exists as early as possible, then each phase adds a source
or an insight without breaking the last.

**Phase 0 — Scaffold + schema.** Repo layout, `pyproject.toml`, `config.toml`, `db.py`
(connection + migration runner), `schema.sql` (§3 raw + unified). `helthi init` creates the db.
CLI skeleton. *Done when:* empty db builds from schema, `helthi` subcommands stubbed.

**Phase 1 — Whoop end-to-end (prove the spine).** OAuth flow, Whoop pull → raw tables →
`unify` populates `day` (recovery + sleep + strain only) → Streamlit dashboard with insight #4's
recovery/HRV/sleep trends. *Done when:* real Whoop data flows ingest→store→view. This alone is
already a useful tool. Dependencies: none.

**Phase 2 — Hevy (CSV drop).** Build the shared file-drop machinery (scan/watch/hash/archive)
here, then the Hevy CSV parser → `hevy_workout/exercise/set` → `unify` fills `hevy_volume_kg`,
populates `session` (strength). Unlocks **insight #1 (recovery vs load)** and **#2 (sleep →
performance)**. Depends on Phase 1's `day`/`unify`. Note: this phase delivers the folder-watch
infra Samsung reuses in Phase 3.

**Phase 3 — Samsung.** Reuse Phase 2's file-drop machinery + the format-aware parser (banner
skip, prefix strip, epoch-ms + `time_offset`, nested-JSON HR) → `samsung_hr`,
`samsung_exercise`. Requires a **real export sample first** (see Risks). *Done when:* HR series
lands in db, sessions populate.

**Phase 4 — Cross-source join layer.** `align_hr_to_sessions()` + `session_hr_zone` +
`session_overlap` view (§3.3c/d), borrowing `drkostas/hevy2garmin`'s HR-onto-strength-workout
alignment logic. Unlocks **insight #3 (HR zones per workout)**. Depends on Phases 2+3.

**Phase 5 — Polish.** ACWR gauge, per-lift small multiples, estimated/clock-skew flags in UI,
`launchd`/cron for scheduled pulls, Datasette-on-the-side for debugging. Defer anything here
that isn't pulling weight.

Deferable / explicitly later: Whoop/Samsung cardio sessions into `session` (only Hevy strength
at first); travel-tz correction; write-back (never).

---

## 7. Risks & open questions

1. **Samsung export format is the trap (highest).** Prior art tells us the *shape* (banner line,
   `com.samsung.shealth.*` prefixes, epoch-ms + `time_offset`, HR in nested JSON, integer sport
   codes), but the format **drifts between app versions** and the best reference (BlackFireAlex)
   is unlicensed and from 2022. *Mitigation:* build the parser tolerant (prefix-strip, epoch-ms
   auto-detect, nested-JSON follow), cross-check against `davidmosiah/samsung-health-mcp` (2026),
   isolate in `parsers/samsung.py`, archive raw so a fix is a re-parse not a re-export. Phase 3
   is gated on a real sample. **Action for user: provide one real Samsung Health export before
   Phase 3.**

2. **Timezone / travel.** Naive Hevy-CSV and Samsung timestamps are assumed home-tz. Correct at
   home, wrong while traveling — could misassign a workout's day or misalign HR by hours.
   *Mitigation:* store everything UTC + a `home_tz` config; PAD + clock-skew guard in the HR
   join; flag suspicious zero-overlap sessions. Full per-record tz correction deferred as
   over-engineering for a mostly-home user.

3. **Whoop rate limits & token refresh.** 100/min, 10k/day caps; refresh tokens rotate.
   *Mitigation:* the vendored `hedgertronic/whoop` handles refresh via `offline` scope + the
   `on_token_refresh` persistence callback (we just wire it to storage); watermark cursor keeps
   steady-state pulls tiny; 429 backoff; CLI re-auth path when refresh hard-fails; never assume a
   pull is complete without checking `ingest_run.status`.

4. **Hevy CSV is now the only Hevy path (paywall resolved by design).** No Hevy Pro → no API,
   so ingestion is manual export. *Consequence, not a risk:* Hevy data is only as fresh as the
   user's last export; CSV lacks a server id and precise end times (handled by synthesized ids +
   end-time estimation). If the user ever gets Pro, an API parser can be added without schema
   change — the `hevy_*` tables are source-shape-neutral.

5. **HR-onto-session join correctness.** Sessions with missing end times (Hevy CSV) and
   watch/app clock skew can produce empty or wrong zones. *Mitigation:* end-time estimation with
   an "estimated" flag, ±PAD window, gap-weighted zone bucketing, and an explicit "possible clock
   offset" note surfaced in the UI rather than silent bad data.

Open decisions needing the user:
- Confirm **home timezone** default (`Asia/Dubai`?) and HR-zone model (age-based vs measured
  max HR).
- Provide a **Samsung export sample** to finalize the parser (blocks Phase 3).
- (Hevy Pro question resolved: no Pro → Hevy is CSV-only, decided.)

---

## 8. Handoff summary (for the GM)

- **Backend** owns: `db.py`/`schema.sql`, all three `parsers/*` modules, `unify.py`,
  `time_align.py` (the join layer — the hardest and most valuable piece), `insights.py` compute
  functions. Reuse prior art per `PRIOR-ART.md`: vendor `hedgertronic/whoop` for the Whoop
  layer, mirror `sandseb123/Leo-Health-Core`'s ingestion structure, use `remuzel/hevy-api`'s
  model as the `hevy_*` schema reference, and borrow `drkostas/hevy2garmin`'s HR-overlay logic
  for Phase 4. Deliver phase by phase; Whoop first proves the spine.
- **Frontend** owns: `dashboard/app.py` (Streamlit) — four insight tabs + global date-range
  filter, Plotly charts. Reads *only* the unified layer (`day`, `session`, `session_hr_zone`)
  and calls `insights.py`; never touches raw tables or ingest.
- **Contract between them:** the unified schema in §3.2 + the `insights.py` function signatures
  (one per insight, returning a dataframe/dict keyed by `local_day` or `session_id`). Frontend
  builds against those signatures with stub data while Backend wires real ingestion — they can
  proceed in parallel after Phase 1's `day` table exists.
- **Blocking on user:** Samsung export sample (Phase 3), home-tz + HR-zone confirmation, Hevy
  Pro status.

Schema DDL in §3 is the source of truth — it should land verbatim in `helthi/schema.sql`.
```
